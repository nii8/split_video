import os
import time

from phase2_rewrite.prompts import PROMPT_VIDEO
from shared.llm_caller import call_llm_batch, call_llm_stream


def run_phase2(
    phase1_text,
    prompt=PROMPT_VIDEO,
    output_dir=None,
    output_path=None,
    interactive=False,
    stream=False,
    heartbeat_callback=None,
):
    phase_start = time.time()

    if output_path is None and output_dir:
        output_path = os.path.join(output_dir, "step2.txt")

    if output_path and os.path.exists(output_path):
        print(f"[跳过] 已有缓存: {output_path}")
        with open(output_path, "r", encoding="utf-8") as f:
            return f.read()

    full_prompt = prompt + "\n" + phase1_text
    print("[Stage 2] 调用 LLM ...")
    if stream:
        result = call_llm_stream(full_prompt)
    else:
        result = call_llm_batch(full_prompt, heartbeat_callback=heartbeat_callback)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[Stage 2] 已保存: {output_path}")
    print(f"[Stage 2] duration: {round(time.time() - phase_start, 2)} s")
    return result


def run_phase2_batch(video_id, phase1_content, output_path, prompt=PROMPT_VIDEO, heartbeat_callback=None):
    return run_phase2(
        phase1_content,
        prompt=prompt,
        output_path=output_path,
        interactive=False,
        stream=False,
        heartbeat_callback=heartbeat_callback,
    )

