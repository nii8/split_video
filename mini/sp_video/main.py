import argparse
import json
import os
import sys

from phase1_select.prompts import PROMPT_VIDEO as PHASE1_PROMPT
from phase1_select.runner import run_phase1, run_phase1_batch
from phase2_rewrite.prompts import PROMPT_VIDEO as PHASE2_PROMPT
from phase2_rewrite.runner import run_phase2, run_phase2_batch
from phase3_match.runner import run_phase3
from phase4_cut.runner import run_phase4


def exit_json(data):
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0 if data.get("status") == "success" else 1)


def ask_input(label):
    value = input(f"{label}: ").strip()
    while not value:
        print("不能为空，请重新输入")
        value = input(f"{label}: ").strip()
    return value


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


def confirm_continue(msg):
    input(f"\n{msg} [按回车继续]")


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
    interactive = args.input_video is None

    print("智能视频剪辑 CLI")
    print("=" * 60)

    if interactive:
        video_path = ask_input("请输入视频路径 (.mp4)")
        srt_path = ask_input("请输入字幕路径 (.srt)")
    else:
        video_path = args.input_video
        srt_path = args.input_srt
        if not video_path or not srt_path:
            exit_json({"status": "error", "stage": 0, "message": "--input_video 和 --input_srt 均为必填项"})

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

    video_id = os.path.basename(video_path).replace(".mp4", "")
    output_dir = args.output_dir if args.output_dir else os.path.dirname(os.path.abspath(video_path))
    os.makedirs(output_dir, exist_ok=True)
    print(f"[Init] video_id={video_id}  output_dir={output_dir}  stage={args.stage}")

    phase1_prompt = PHASE1_PROMPT
    if interactive:
        print("Phase1 提示词（默认）：\n")
        phase1_prompt = edit_multiline(PHASE1_PROMPT)

    try:
        result1 = run_phase1(srt_path, prompt=phase1_prompt, output_dir=output_dir, stream=True)
    except Exception as e:
        msg = f"Phase 1 失败: {e}"
        if interactive:
            print(msg)
            sys.exit(1)
        exit_json({"status": "error", "stage": 1, "message": msg})

    if args.stage == 1:
        if interactive:
            print("\n[完成] 已执行到 Stage 1")
            return
        exit_json({"status": "success", "output": os.path.join(output_dir, "step1.txt")})

    if interactive:
        confirm_continue("第一阶段完成，准备进入第二阶段")

    phase2_prompt = PHASE2_PROMPT
    if interactive:
        print("Phase2 提示词（默认）：\n")
        phase2_prompt = edit_multiline(PHASE2_PROMPT)

    try:
        result2 = run_phase2(result1, prompt=phase2_prompt, output_dir=output_dir, stream=True)
    except Exception as e:
        msg = f"Phase 2 失败: {e}"
        if interactive:
            print(msg)
            sys.exit(1)
        exit_json({"status": "error", "stage": 2, "message": msg})

    if args.stage == 2:
        if interactive:
            print("\n[完成] 已执行到 Stage 2")
            return
        exit_json({"status": "success", "output": os.path.join(output_dir, "step2.txt")})

    if interactive:
        confirm_continue("第二阶段完成，准备生成时间序列（第三阶段）")

    try:
        keep_intervals = run_phase3(srt_path, result2, output_dir=output_dir)
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

    if args.stage == 3:
        if interactive:
            print("\n[完成] 已执行到 Stage 3")
            return
        exit_json({"status": "success", "output": os.path.join(output_dir, "intervals.json")})

    if interactive:
        confirm_continue("确认以上片段，准备生成视频（第四阶段）")

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


if __name__ == "__main__":
    main()
