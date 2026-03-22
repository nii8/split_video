#!/usr/bin/env python3
"""
skill.py — sp_video 技能入口

OpenClaw 通过子进程调用，所有标准输出为 JSON，进度日志输出到 stderr。

用法：
    python skill.py list
    python skill.py start --video_id 7Q3A0006
    python skill.py phase2 --video_id 7Q3A0006 [--prompt_file /tmp/p.txt]
    python skill.py generate --video_id 7Q3A0006
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime

# 确保可以 import 同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import settings
from main import run_phase1, run_phase2, run_phase3, run_phase4, PHASE2_PROMPT

# ── 常量 ──────────────────────────────────────────────────────────────────────
OSS_SOURCE_BASE = "oss://kaixin-v/hanbing/2026"
OSS_DEST_BASE   = "oss://kaixin1109/hanbing/2026"
VIDEO_URL_BASE  = "http://video.kaixin.wiki/hanbing/2026"
DATA_DIR        = "./data/hanbing"
CACHE_FILE      = "./data/video_cache.json"
STATE_DIR       = "./data/skill_state"


# ── 输出工具 ──────────────────────────────────────────────────────────────────
def out(data):
    """输出 JSON 并退出（success→0，error→1）"""
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(0 if data.get('status') != 'error' else 1)


def log(msg):
    """进度日志输出到 stderr，不影响 JSON stdout"""
    print(f'[skill] {msg}', file=sys.stderr, flush=True)


# ── 缓存 / 状态工具 ───────────────────────────────────────────────────────────
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def load_state(video_id):
    state_file = os.path.join(STATE_DIR, video_id, 'state.json')
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_state(video_id, state):
    state_dir = os.path.join(STATE_DIR, video_id)
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, 'state.json'), 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ── OSS 工具 ──────────────────────────────────────────────────────────────────
def oss_ls():
    """列出 OSS 上的文件路径列表"""
    result = subprocess.run(
        ['ossutil', 'ls', OSS_SOURCE_BASE],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().split('\n')
    # 跳过第一行（头部），从每行提取 oss:// 开头的路径
    paths = []
    for l in lines[1:]:
        # ossutil 输出格式：每行末尾是 oss://... 路径
        idx = l.find('oss://')
        if idx != -1:
            path = l[idx:].strip()
            if not path.endswith('/'):  # 过滤目录
                paths.append(path)
    return paths


def parse_oss_paths(paths):
    """
    从 OSS 路径列表提取成对的 mp4+srt 信息。

    路径层级不固定，但 video_id 始终是倒数第二段，filename 是最后一段：
      oss://kaixin-v/hanbing/2026/{month}/[.../{batch}/]{video_id}/{filename}
    返回：{video_id: {month, batch, oss_base, mp4_name, srt_name, has_mp4, has_srt}}
    """
    prefix = OSS_SOURCE_BASE.rstrip('/')
    video_map = {}

    for path in paths:
        if not path.endswith('.mp4') and not path.endswith('.srt'):
            continue
        rel = path[len(prefix):]
        parts = rel.strip('/').split('/')
        if len(parts) < 2:
            continue
        filename = parts[-1]
        video_id = filename.rsplit('.', 1)[0]  # 始终用文件名作为 video_id
        month = parts[0] if len(parts) >= 1 else ''
        batch = '/'.join(p for p in parts[1:-2] if p != 'ff') if len(parts) > 2 else ''
        oss_base = path[:path.rfind('/')]

        if video_id not in video_map:
            video_map[video_id] = {
                'month': month,
                'batch': batch,
                'oss_base': oss_base,
                'has_mp4': False,
                'has_srt': False,
            }
        if filename.endswith('.mp4'):
            video_map[video_id]['has_mp4'] = True
            video_map[video_id]['mp4_name'] = filename
        elif filename.endswith('.srt'):
            video_map[video_id]['has_srt'] = True
            video_map[video_id]['srt_name'] = filename

    # 只保留 mp4 和 srt 都存在的
    return {vid: info for vid, info in video_map.items()
            if info['has_mp4'] and info['has_srt']}


def oss_download(oss_path, local_path):
    """从 OSS 下载单个文件（强制覆盖）"""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    subprocess.run(['ossutil', 'cp', oss_path, local_path, '-f'], check=True)


def oss_upload(local_path, oss_dest):
    """上传文件到 OSS（强制覆盖）"""
    subprocess.run(['ossutil', 'cp', local_path, oss_dest, '-f'], check=True)


# ── LLM 工具 ─────────────────────────────────────────────────────────────────
def generate_summary(srt_path):
    """用 LLM 为 SRT 字幕生成 2-3 句话摘要"""
    from openai import OpenAI
    with open(srt_path, 'r', encoding='utf-8') as f:
        srt_content = f.read()

    # 只取前 4000 字符，避免超 token
    srt_snippet = srt_content[:4000]

    client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url='https://api.deepseek.com')
    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[
            {'role': 'system', 'content': '你是视频内容分析师，请用 2-3 句话概括视频主要内容，语言简洁。'},
            {'role': 'user', 'content': f'以下是视频字幕，请生成简短摘要：\n\n{srt_snippet}'},
        ]
    )
    return resp.choices[0].message.content.strip()


# ── 子命令实现 ────────────────────────────────────────────────────────────────
def cmd_list(_args):
    """查询 OSS 视频列表，生成/更新摘要缓存"""
    log('查询 OSS 文件列表...')
    try:
        paths = oss_ls()
    except Exception as e:
        out({'status': 'error', 'message': f'ossutil 查询失败: {e}'})

    oss_videos = parse_oss_paths(paths)
    log(f'OSS 上找到 {len(oss_videos)} 个成对视频')

    cache = load_cache()

    # 删除 OSS 已不存在的条目
    removed = [vid for vid in list(cache.keys()) if vid not in oss_videos]
    for vid in removed:
        del cache[vid]
        log(f'已从缓存移除已删除视频: {vid}')

    # 新视频：下载 SRT → 生成摘要
    new_count = 0
    for video_id, info in oss_videos.items():
        if video_id not in cache:
            log(f'新视频 {video_id}，下载 SRT 并生成摘要...')
            try:
                local_dir = os.path.join(DATA_DIR, video_id)
                local_srt = os.path.join(local_dir, info['srt_name'])
                if not os.path.exists(local_srt):
                    oss_download(f"{info['oss_base']}/{info['srt_name']}", local_srt)
                summary = generate_summary(local_srt)
            except Exception as e:
                summary = f'摘要生成失败: {e}'
                log(f'警告: {video_id} 摘要生成失败: {e}')

            cache[video_id] = {
                'oss_base':  info['oss_base'],
                'month':     info['month'],
                'batch':     info['batch'],
                'mp4_name':  info['mp4_name'],
                'srt_name':  info['srt_name'],
                'summary':   summary,
                'cached_at': datetime.now().strftime('%Y-%m-%d'),
            }
            new_count += 1
        else:
            # 更新元数据（路径可能变化）
            cache[video_id].update({
                'oss_base': info['oss_base'],
                'month':    info['month'],
                'batch':    info['batch'],
                'mp4_name': info['mp4_name'],
                'srt_name': info['srt_name'],
            })

    save_cache(cache)

    videos = [
        {'id': vid, 'summary': info['summary'], 'month': info['month'], 'batch': info['batch']}
        for vid, info in cache.items()
    ]

    out({
        'status':  'success',
        'total':   len(videos),
        'new':     new_count,
        'removed': len(removed),
        'videos':  videos,
    })


def cmd_start(args):
    """下载视频文件 + 自动执行 Phase1 + 返回 Phase2 提示词"""
    video_id = args.video_id
    cache = load_cache()

    if video_id not in cache:
        out({'status': 'error', 'message': f'视频 {video_id} 不在缓存中，请先运行 list'})

    info = cache[video_id]
    local_dir = os.path.join(DATA_DIR, video_id)
    local_srt = os.path.join(local_dir, info['srt_name'])
    local_mp4 = os.path.join(local_dir, info['mp4_name'])

    # 下载文件（已存在则跳过）
    if not os.path.exists(local_srt):
        log(f'下载 SRT: {info["srt_name"]}')
        oss_download(f"{info['oss_base']}/{info['srt_name']}", local_srt)

    if not os.path.exists(local_mp4):
        log(f'下载 MP4: {info["mp4_name"]}（可能较慢）')
        oss_download(f"{info['oss_base']}/{info['mp4_name']}", local_mp4)

    # 初始化 state
    state = {
        'video_id':   video_id,
        'srt_path':   local_srt,
        'video_path': local_mp4,
        'oss_month':  info['month'],
        'oss_batch':  info['batch'],
        'phase':      1,
    }
    save_state(video_id, state)

    # Phase1 自动执行（非交互）
    state_dir = os.path.join(STATE_DIR, video_id)
    log('执行 Phase1（LLM 筛选字幕）...')
    try:
        result1 = run_phase1(local_srt, output_dir=state_dir, interactive=False)
    except Exception as e:
        out({'status': 'error', 'stage': 1, 'message': str(e)})

    state['phase'] = 2
    save_state(video_id, state)

    preview = result1[:600] + '...' if len(result1) > 600 else result1

    out({
        'status':         'need_confirm_prompt',
        'video_id':       video_id,
        'message':        'Phase1 完成。以下是 Phase2 的默认提示词，可直接确认或修改后通过 --prompt_file 传入。',
        'default_prompt': PHASE2_PROMPT,
        'phase1_preview': preview,
    })


def cmd_phase2(args):
    """Phase2（LLM 重组脚本）+ Phase3（AI 字幕匹配）→ 返回时间序列"""
    video_id = args.video_id
    state = load_state(video_id)

    if not state:
        out({'status': 'error', 'message': f'找不到 {video_id} 的处理状态，请先运行 start'})
    if state.get('phase', 0) < 2:
        out({'status': 'error', 'message': 'Phase1 尚未完成，请先运行 start'})

    state_dir = os.path.join(STATE_DIR, video_id)

    # 读取自定义提示词（可选）
    custom_prompt = None
    if args.prompt_file:
        if not os.path.exists(args.prompt_file):
            out({'status': 'error', 'message': f'提示词文件不存在: {args.prompt_file}'})
        with open(args.prompt_file, 'r', encoding='utf-8') as f:
            custom_prompt = f.read().strip()
        log(f'使用自定义提示词（{len(custom_prompt)} 字符）')

    # 如有自定义 prompt，清除 step2 缓存以强制重新生成
    step2_path = os.path.join(state_dir, 'step2.txt')
    if custom_prompt and os.path.exists(step2_path):
        os.remove(step2_path)
        log('已清除 step2 缓存')

    # 读取 step1 结果
    step1_path = os.path.join(state_dir, 'step1.txt')
    if not os.path.exists(step1_path):
        out({'status': 'error', 'message': 'step1.txt 不存在，请重新运行 start'})
    with open(step1_path, 'r', encoding='utf-8') as f:
        result1 = f.read()

    # Phase2：如有自定义 prompt，临时替换模块全局变量
    log('执行 Phase2（LLM 脚本重组）...')
    try:
        import main as main_module
        if custom_prompt:
            original_prompt = main_module.PHASE2_PROMPT
            main_module.PHASE2_PROMPT = custom_prompt
        result2 = run_phase2(result1, output_dir=state_dir, interactive=False)
        if custom_prompt:
            main_module.PHASE2_PROMPT = original_prompt
    except Exception as e:
        out({'status': 'error', 'stage': 2, 'message': str(e)})

    # Phase3：清除旧 intervals 缓存，确保用最新 step2 重新匹配
    intervals_path = os.path.join(state_dir, 'intervals.json')
    if os.path.exists(intervals_path):
        os.remove(intervals_path)

    log('执行 Phase3（AI 字幕时间轴匹配）...')
    try:
        keep_intervals = run_phase3(state['srt_path'], result2, output_dir=state_dir)
    except Exception as e:
        out({'status': 'error', 'stage': 3, 'message': str(e)})

    if not keep_intervals:
        out({'status': 'error', 'stage': 3, 'message': '未匹配到任何时间片段，请检查字幕或调整脚本'})

    state['phase'] = 3
    save_state(video_id, state)

    intervals_display = [
        {
            'index': i + 1,
            'start': item[0][0],
            'end':   item[0][1],
            'text':  str(item[1])[:80],
        }
        for i, item in enumerate(keep_intervals)
    ]

    out({
        'status':    'need_confirm_intervals',
        'video_id':  video_id,
        'message':   f'已匹配 {len(keep_intervals)} 个片段，确认后调用 generate 生成视频。',
        'count':     len(keep_intervals),
        'intervals': intervals_display,
    })


def cmd_generate(args):
    """Phase4（ffmpeg 剪辑）→ 上传 OSS → 返回视频 URL"""
    video_id = args.video_id
    state = load_state(video_id)

    if not state:
        out({'status': 'error', 'message': f'找不到 {video_id} 的处理状态，请先运行 start'})
    if state.get('phase', 0) < 3:
        out({'status': 'error', 'message': 'Phase3 尚未完成，请先运行 phase2'})

    state_dir = os.path.join(STATE_DIR, video_id)
    intervals_path = os.path.join(state_dir, 'intervals.json')

    if not os.path.exists(intervals_path):
        out({'status': 'error', 'message': 'intervals.json 不存在，请重新运行 phase2'})

    with open(intervals_path, 'r', encoding='utf-8') as f:
        keep_intervals = json.load(f)

    # Phase4：生成视频
    log(f'执行 Phase4（ffmpeg 剪辑 {len(keep_intervals)} 个片段）...')
    try:
        output_path = run_phase4(state['video_path'], keep_intervals, video_id)
    except Exception as e:
        out({'status': 'error', 'stage': 4, 'message': str(e)})

    if not output_path or not os.path.exists(output_path):
        out({'status': 'error', 'stage': 4, 'message': '视频文件生成失败'})

    # 构造 OSS 路径和公网 URL
    filename  = os.path.basename(output_path)
    month     = state['oss_month']
    batch     = state['oss_batch']
    mid = f"{batch}/" if batch else ""
    oss_dest  = f"{OSS_DEST_BASE}/{month}/{mid}{video_id}/{filename}"
    video_url = f"{VIDEO_URL_BASE}/{month}/{mid}{video_id}/{filename}"

    # 上传到 OSS
    log(f'上传到 OSS: {oss_dest}')
    try:
        oss_upload(output_path, oss_dest)
    except Exception as e:
        out({'status': 'error', 'stage': 4, 'message': f'OSS 上传失败: {e}'})

    log(f'完成！URL: {video_url}')

    out({
        'status':   'success',
        'video_id': video_id,
        'filename': filename,
        'oss_path': oss_dest,
        'url':      video_url,
        'message':  '视频生成并上传成功！',
    })


# ── 主入口 ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='sp_video 技能 — OpenClaw 调用接口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest='cmd', required=True)

    # list
    sub.add_parser('list', help='查询 OSS 视频列表并更新摘要缓存')

    # start
    p_start = sub.add_parser('start', help='开始处理视频（Phase1，自动执行）')
    p_start.add_argument('--video_id', required=True, help='视频编号，如 7Q3A0006')

    # phase2
    p_p2 = sub.add_parser('phase2', help='生成脚本并匹配时间轴（Phase2+3）')
    p_p2.add_argument('--video_id', required=True, help='视频编号')
    p_p2.add_argument('--prompt_file', default=None,
                      help='自定义 Phase2 提示词文件路径（不传则使用默认提示词）')

    # generate
    p_gen = sub.add_parser('generate', help='生成视频并上传 OSS（Phase4）')
    p_gen.add_argument('--video_id', required=True, help='视频编号')

    args = parser.parse_args()

    if args.cmd == 'list':
        cmd_list(args)
    elif args.cmd == 'start':
        cmd_start(args)
    elif args.cmd == 'phase2':
        cmd_phase2(args)
    elif args.cmd == 'generate':
        cmd_generate(args)


if __name__ == '__main__':
    main()
