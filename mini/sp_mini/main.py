import os
import sys
import json
import argparse
import time
from openai import OpenAI
import settings
from make_time.step2 import get_keep_intervals
from make_video.step3 import cut_video_main


PHASE1_PROMPT = """核心指令： 请你担任一位短视频顺序压缩编辑，严格遵守以下原则：
1.零创作原则： 你输出的每一个句子片段，必须原封不动、一字不差地来自附件字幕文件。严禁任何形式的改写、概括、提炼或拼接。
2.时间轴对应原则： 每个筛选出的句子片段都必须附带其原始的精确时间轴。

你的任务：
仔细阅读附件字幕文件的全部内容。
从中筛选出符合以下特质的原始句子片段：
1.能够保留原叙事主线、原论述主线的句子。
2.能够保留观点、结论、关键解释、关键案例、关键转折、关键结果的句子。
3.能够与前后内容自然衔接、尽量独立成立的句子。
4.必要时宁可保留一小段连续表达，也不要只留下无法独立理解的半句、碎句。
5.只有在明显属于寒暄、口头禅、重复表达、空泛铺垫、无信息增量内容时才优先删除。

筛选时额外遵守以下约束：
1.这次目标不是做1到2分钟的金句摘录，而是做约5分钟的单条顺序压缩版。
2.如果原视频明显长于5分钟，你需要保留足够素材，让下一阶段有可能组织出约4到6分钟的成片。
3.如果原视频本身接近5分钟，原则上只删除明显废话，不要过度压缩。
4.不要只挑“最炸”的句子；要优先保留能把事情讲清楚的句子。
5.尽量避免输出时长过短的碎句，尤其避免大量少于2秒、脱离上下文难以理解的片段。

输出时，仅需列出筛选出的句子及其对应时间轴，无需进行任何顺序调整或组合。
输出格式要求：
请按以下格式输出，严格保持每行结构清晰：

(原始时间轴) --> (原始时间轴)
(完全摘自附件的原始文案)

输出格式示例如下：

00:00:19,833 --> 00:00:20,633
知己知彼

00:00:27,400 --> 00:00:30,300
不是99% 是99.99%"""


PHASE2_PROMPT = """核心指令： 请你担任一位短视频顺序压缩编辑。
严格遵守以下原则：
1.零创作原则： 你输出的每一个句子片段，必须原封不动、一字不差地来自附件字幕文件。严禁任何形式的改写、概括、提炼或拼接。
2.时间轴对应原则： 每个筛选出的句子片段都必须附带其原始的精确时间轴。
3.顺序原则： 你必须严格遵守原字幕的时间顺序组织脚本，原则上禁止调换顺序，禁止把后面的内容提前到前面。

你的任务：
根据提供的筛选句子片段库为唯一素材来源（即一系列带有时间轴的原始句子片段）。
重组与排序： 将这些原始句子片段，在不改变原时间顺序的前提下进行删减和组织，形成一个尽量完整、顺畅、便于观看的顺序压缩版脚本。

叙事逻辑：
a. 开头尽量快速进入主题，但不要为了钩子破坏原始顺序。
b. 中间优先保留“问题/背景 -> 解释/案例 -> 转折/感悟 -> 结论/结果”的自然推进。
c. 结尾优先保留原视频中自然收束、总结、升华的位置，不要为了短视频感强行只留口号句。

严格遵守红线： 脚本中的每一句话都必须源自提供的素材库，且时间轴与文案严格对应，严禁任何创作或修改。
这次脚本目标是生成约4到6分钟成片；如果素材库本身不足以达到5分钟，也要优先保证内容完整，避免压成过短的金句拼贴。
你的工作重点是顺序压缩，而不是重新改写叙事结构。
优先删除重复铺垫、冗长过渡、相近意思的重复句、无实质推进的话。
尽量保留较完整的表达单元，不要输出大量缺主语、缺宾语、脱离上下文难懂的残句。
除非确有必要，尽量避免输出少于2秒的短碎片。

输出格式要求：
请按以下格式输出最终脚本：

(原始时间轴) --> (原始时间轴)
(完全摘自附件的原始文案)

输出格式示例如下：

00:00:19,833 --> 00:00:20,633
知己知彼

00:00:27,400 --> 00:00:30,300
不是99% 是99.99%

筛选句子片段库：
"""


def exit_json(data):
    """输出最终 JSON 并退出"""
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0 if data.get("status") == "success" else 1)


def ask_input(label):
    val = input(f"{label}: ").strip()
    while not val:
        print("不能为空，请重新输入")
        val = input(f"{label}: ").strip()
    return val


def edit_multiline(default):
    print(default)
    print("\n[直接回车使用默认，输入 e 进入编辑]")
    choice = input("> ").strip().lower()
    if choice != "e":
        return default
    print("粘贴新提示词，完成后新行输入 END 回车：")
    lines = []
    while True:
        line = input()
        if line == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def call_llm_stream(prompt):
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.BAILIAN_API_KEY,
        base_url="https://coding.dashscope.aliyuncs.com/v1",
        timeout=900,
    )
    start = time.time()
    response = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[
            {
                "role": "system",
                "content": "You are a senior short video copywriter well-versed in the dissemination patterns of the TikTok platform.",
            },
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )
    full = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            word = chunk.choices[0].delta.content
            print(word, end="", flush=True)
            full += word
    print()
    print(f"[LLM] stream call duration: {round(time.time() - start, 2)} s")
    return full


def call_llm_batch(prompt):
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.BAILIAN_API_KEY,
        base_url="https://coding.dashscope.aliyuncs.com/v1",
        timeout=900,
    )
    start = time.time()
    response = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[
            {
                "role": "system",
                "content": "You are a senior short video copywriter well-versed in the dissemination patterns of the TikTok platform.",
            },
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    print(f"[LLM] batch call duration: {round(time.time() - start, 2)} s")
    return response.choices[0].message.content


def confirm_continue(msg):
    input(f"\n{msg} [按回车继续]")


def run_phase1(srt_path, output_dir=None, interactive=True):
    print("\n" + "=" * 60)
    print("[第一阶段] LLM 筛选有价值字幕")
    print("=" * 60)
    phase_start = time.time()

    # 若 output_dir 下已有 step1.txt，直接复用
    step1_path = os.path.join(output_dir, "step1.txt") if output_dir else None
    if step1_path and os.path.exists(step1_path):
        print(f"[跳过] 已有缓存: {step1_path}")
        with open(step1_path, "r", encoding="utf-8") as f:
            return f.read()

    prompt = PHASE1_PROMPT
    if interactive:
        print("提示词（默认）：\n")
        prompt = edit_multiline(PHASE1_PROMPT)

    print(f"[Stage 1] 读取字幕: {srt_path}")
    srt_content = open(srt_path, "r", encoding="utf-8").read()
    full_prompt = prompt + "\n\n" + srt_content
    print("[Stage 1] 调用 LLM ...")
    print("\n--- LLM 输出 ---\n")
    result = call_llm_stream(full_prompt)

    if step1_path:
        with open(step1_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[Stage 1] 已保存: {step1_path}")
    print(f"[Stage 1] duration: {round(time.time() - phase_start, 2)} s")

    return result


def run_phase2(phase1_result, output_dir=None, interactive=True):
    print("\n" + "=" * 60)
    print("[第二阶段] LLM 重组脚本")
    print("=" * 60)
    phase_start = time.time()

    step2_path = os.path.join(output_dir, "step2.txt") if output_dir else None
    if step2_path and os.path.exists(step2_path):
        print(f"[跳过] 已有缓存: {step2_path}")
        with open(step2_path, "r", encoding="utf-8") as f:
            return f.read()

    prompt = PHASE2_PROMPT
    if interactive:
        print("提示词（默认）：\n")
        prompt = edit_multiline(PHASE2_PROMPT)

    full_prompt = prompt + "\n" + phase1_result
    print("[Stage 2] 调用 LLM ...")
    print("\n--- LLM 输出 ---\n")
    result = call_llm_stream(full_prompt)

    if step2_path:
        with open(step2_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[Stage 2] 已保存: {step2_path}")
    print(f"[Stage 2] duration: {round(time.time() - phase_start, 2)} s")

    return result


def run_phase3(srt_path, script, output_dir=None):
    print("\n" + "=" * 60)
    print("[第三阶段] 生成时间序列（AI 字幕匹配）")
    print("=" * 60)
    phase_start = time.time()

    intervals_path = os.path.join(output_dir, "intervals.json") if output_dir else None
    if intervals_path and os.path.exists(intervals_path):
        print(f"[跳过] 已有缓存: {intervals_path}")
        with open(intervals_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print("[Stage 3] 开始 AI 字幕匹配 ...")
    result = get_keep_intervals(srt_path, script)
    keep_intervals = result.get("keep_intervals", [])
    valid = [item for item in keep_intervals if item[0][0]]
    skipped = len(keep_intervals) - len(valid)
    print(f"[Stage 3] 共匹配 {len(valid)} 个片段（{skipped} 个未匹配已跳过）：")
    for i, item in enumerate(valid):
        start, end = item[0]
        text = str(item[1])
        print(f"  {i + 1}. [{start} --> {end}] {text[:40]}")

    if intervals_path:
        with open(intervals_path, "w", encoding="utf-8") as f:
            json.dump(valid, f, ensure_ascii=False, indent=2)
        print(f"[Stage 3] 已保存: {intervals_path}")
    print(f"[Stage 3] duration: {round(time.time() - phase_start, 2)} s")

    return valid


def run_phase4(video_path, keep_intervals, video_id):
    print("\n" + "=" * 60)
    print("[第四阶段] 生成视频")
    print("=" * 60)
    phase_start = time.time()
    print(f"[Stage 4] 开始剪辑，共 {len(keep_intervals)} 个片段 ...")
    output_path = cut_video_main(keep_intervals, video_path, video_id, "cli")
    print(f"[Stage 4] 视频已生成: {output_path}")
    print(f"[Stage 4] duration: {round(time.time() - phase_start, 2)} s")
    return output_path


def run_phase1_batch(video_id, srt_path, output_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    full_prompt = PHASE1_PROMPT + "\n\n" + srt_content
    result = call_llm_batch(full_prompt)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return result


def run_phase2_batch(video_id, phase1_content, output_path):
    full_prompt = PHASE2_PROMPT + "\n" + phase1_content
    result = call_llm_batch(full_prompt)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return result


def parse_args():
    parser = argparse.ArgumentParser(description="智能视频剪辑 CLI")
    parser.add_argument("--input_video", help="视频路径 (.mp4)")
    parser.add_argument("--input_srt", help="字幕路径 (.srt)")
    parser.add_argument("--output_dir", help="中间文件输出目录（默认与视频同目录）")
    parser.add_argument(
        "--stage",
        type=int,
        choices=[1, 2, 3, 4],
        default=4,
        help="执行到第几阶段（1~4，默认 4 全跑）",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    interactive = args.input_video is None  # 没传参数 → 交互模式

    print("智能视频剪辑 CLI")
    print("=" * 60)

    # ── 获取输入 ──────────────────────────────────────────────────
    if interactive:
        video_path = ask_input("请输入视频路径 (.mp4)")
        srt_path = ask_input("请输入字幕路径 (.srt)")
    else:
        video_path = args.input_video
        srt_path = args.input_srt
        if not video_path or not srt_path:
            exit_json(
                {
                    "status": "error",
                    "stage": 0,
                    "message": "--input_video 和 --input_srt 均为必填项",
                }
            )

    # ── 校验文件 ──────────────────────────────────────────────────
    if not os.path.exists(video_path):
        msg = f"视频文件不存在: {video_path}"
        if interactive:
            print(msg)
            sys.exit(1)
        exit_json({"status": "error", "stage": 0, "message": msg})

    if not os.path.exists(srt_path):
        msg = f"字幕文件不存在: {srt_path}"
        if interactive:
            print(msg)
            sys.exit(1)
        exit_json({"status": "error", "stage": 0, "message": msg})

    # ── 准备输出目录 ───────────────────────────────────────────────
    video_id = os.path.basename(video_path).replace(".mp4", "")
    output_dir = (
        args.output_dir
        if args.output_dir
        else os.path.dirname(os.path.abspath(video_path))
    )
    os.makedirs(output_dir, exist_ok=True)
    print(f"[Init] video_id={video_id}  output_dir={output_dir}  stage={args.stage}")

    stage = args.stage

    # ── Phase 1 ───────────────────────────────────────────────────
    try:
        result1 = run_phase1(srt_path, output_dir, interactive)
    except Exception as e:
        msg = f"Phase 1 失败: {e}"
        if interactive:
            print(msg)
            sys.exit(1)
        exit_json({"status": "error", "stage": 1, "message": msg})

    if stage == 1:
        if interactive:
            print("\n[完成] 已执行到 Stage 1")
        else:
            exit_json(
                {"status": "success", "output": os.path.join(output_dir, "step1.txt")}
            )
        return

    if interactive:
        confirm_continue("第一阶段完成，准备进入第二阶段")

    # ── Phase 2 ───────────────────────────────────────────────────
    try:
        result2 = run_phase2(result1, output_dir, interactive)
    except Exception as e:
        msg = f"Phase 2 失败: {e}"
        if interactive:
            print(msg)
            sys.exit(1)
        exit_json({"status": "error", "stage": 2, "message": msg})

    if stage == 2:
        if interactive:
            print("\n[完成] 已执行到 Stage 2")
        else:
            exit_json(
                {"status": "success", "output": os.path.join(output_dir, "step2.txt")}
            )
        return

    if interactive:
        confirm_continue("第二阶段完成，准备生成时间序列（第三阶段）")

    # ── Phase 3 ───────────────────────────────────────────────────
    try:
        keep_intervals = run_phase3(srt_path, result2, output_dir)
    except Exception as e:
        msg = f"Phase 3 失败: {e}"
        if interactive:
            print(msg)
            sys.exit(1)
        exit_json({"status": "error", "stage": 3, "message": msg})

    if not keep_intervals:
        msg = "未匹配到任何时间片段，请检查字幕文件或脚本内容"
        if interactive:
            print(f"\n[错误] {msg}")
            sys.exit(1)
        exit_json({"status": "error", "stage": 3, "message": msg})

    if stage == 3:
        if interactive:
            print("\n[完成] 已执行到 Stage 3")
        else:
            exit_json(
                {
                    "status": "success",
                    "output": os.path.join(output_dir, "intervals.json"),
                }
            )
        return

    if interactive:
        confirm_continue("确认以上片段，准备生成视频（第四阶段）")

    # ── Phase 4 ───────────────────────────────────────────────────
    try:
        output_path = run_phase4(video_path, keep_intervals, video_id)
    except Exception as e:
        msg = f"Phase 4 失败: {e}"
        if interactive:
            print(msg)
            sys.exit(1)
        exit_json({"status": "error", "stage": 4, "message": msg})

    if interactive:
        print(f"\n[完成] 输出视频: {output_path}")
    else:
        exit_json({"status": "success", "output": output_path})


# ── 批量模式函数（无交互） ──────────────────────────────────────────
def run_phase1_batch(video_id, srt_path, output_path):
    """批量模式 Phase1：无交互，直接使用默认 prompt"""
    srt_content = open(srt_path, "r", encoding="utf-8").read()
    full_prompt = PHASE1_PROMPT + "\n\n" + srt_content
    result = call_llm_batch(full_prompt)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return result


def run_phase2_batch(video_id, phase1_content, output_path):
    """批量模式 Phase2：无交互，直接使用默认 prompt"""
    full_prompt = PHASE2_PROMPT + "\n" + phase1_content
    result = call_llm_batch(full_prompt)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return result


if __name__ == "__main__":
    main()
