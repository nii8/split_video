import os
import time

from phase1_select.prompts import PROMPT_VIDEO
from shared.llm_caller import call_llm_batch, call_llm_stream


def run_phase1(
    srt_path,
    prompt=PROMPT_VIDEO,
    output_dir=None,
    output_path=None,
    interactive=False,
    stream=False,
    heartbeat_callback=None,
):
    phase_start = time.time()

    if output_path is None and output_dir:
        output_path = os.path.join(output_dir, "step1.txt")

    if output_path and os.path.exists(output_path):
        print(f"[跳过] 已有缓存: {output_path}")
        with open(output_path, "r", encoding="utf-8") as f:
            return f.read()

    print(f"[Stage 1] 读取字幕: {srt_path}")
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    full_prompt = prompt + "\n\n" + srt_content
    print("[Stage 1] 调用 LLM ...")
    if stream:
        result = call_llm_stream(full_prompt)
    else:
        result = call_llm_batch(full_prompt, heartbeat_callback=heartbeat_callback)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[Stage 1] 已保存: {output_path}")
    print(f"[Stage 1] duration: {round(time.time() - phase_start, 2)} s")
    return result


def run_phase1_batch(video_id, srt_path, output_path, prompt=PROMPT_VIDEO, heartbeat_callback=None):
    return run_phase1(
        srt_path,
        prompt=prompt,
        output_path=output_path,
        interactive=False,
        stream=False,
        heartbeat_callback=heartbeat_callback,
    )

