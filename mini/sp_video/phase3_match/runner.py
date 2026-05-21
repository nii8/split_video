import json
import os
import time

from make_time.step2 import get_keep_intervals as _get_keep_intervals


def get_keep_intervals(srt_path, script_text):
    return _get_keep_intervals(srt_path, script_text)


def run_phase3(srt_path, script_text, output_dir=None):
    phase_start = time.time()

    intervals_path = os.path.join(output_dir, "intervals.json") if output_dir else None
    if intervals_path and os.path.exists(intervals_path):
        print(f"[跳过] 已有缓存: {intervals_path}")
        with open(intervals_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print("[Stage 3] 开始 AI 字幕匹配 ...")
    result = get_keep_intervals(srt_path, script_text)
    keep_intervals = result.get("keep_intervals", [])
    valid = [item for item in keep_intervals if item[0][0]]
    skipped = len(keep_intervals) - len(valid)
    print(f"[Stage 3] 共匹配 {len(valid)} 个片段（{skipped} 个未匹配已跳过）")

    if intervals_path:
        with open(intervals_path, "w", encoding="utf-8") as f:
            json.dump(valid, f, ensure_ascii=False, indent=2)
        print(f"[Stage 3] 已保存: {intervals_path}")
    print(f"[Stage 3] duration: {round(time.time() - phase_start, 2)} s")
    return valid

