"""
run_batch_experiments.py

用途：
- 用不同批量参数运行 batch_generator
- 对比每轮生成了多少个视频
- 输出每轮 summary 的核心指标

说明：
- 不使用 pytest
- 这是手动实验脚本，不是测试框架
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import batch_generator
import settings


def parse_int_list(text):
    return [int(item.strip()) for item in text.split(",") if item.strip()]


def read_multi_video_summary():
    summary_path = os.path.join(settings.BATCH_RESULTS_DIR, "multi_video", "summary.json")
    if not os.path.exists(summary_path):
        return None, summary_path
    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f), summary_path


def main():
    parser = argparse.ArgumentParser(description="run batch experiments")
    parser.add_argument("--phase1", default="1,2", help="comma separated phase1 counts")
    parser.add_argument("--phase2", default="1,3", help="comma separated phase2 counts")
    parser.add_argument("--multi", action="store_true", help="enable multi video mode")
    parser.add_argument("--test-mode", action="store_true", help="enable batch test mode")
    args = parser.parse_args()

    phase1_values = parse_int_list(args.phase1)
    phase2_values = parse_int_list(args.phase2)

    old_phase1 = settings.BATCH_PHASE1_COUNT
    old_phase2 = settings.BATCH_PHASE2_COUNT
    old_multi = settings.BATCH_MULTI_VIDEO_ENABLE
    old_test_mode = settings.BATCH_TEST_MODE

    results = []
    try:
        settings.BATCH_MULTI_VIDEO_ENABLE = args.multi
        settings.BATCH_TEST_MODE = args.test_mode

        for phase1_count in phase1_values:
            for phase2_count in phase2_values:
                settings.BATCH_PHASE1_COUNT = phase1_count
                settings.BATCH_PHASE2_COUNT = phase2_count
                start = time.time()
                print("=" * 60)
                print(f"experiment phase1={phase1_count} phase2={phase2_count} multi={settings.BATCH_MULTI_VIDEO_ENABLE}")
                batch_generator.main()
                duration_sec = round(time.time() - start, 2)
                summary, summary_path = read_multi_video_summary()
                result = {
                    "phase1_count": phase1_count,
                    "phase2_count": phase2_count,
                    "duration_sec": duration_sec,
                    "summary_path": summary_path,
                    "videos_generated": 0,
                    "total_candidates": 0,
                }
                if summary:
                    result["videos_generated"] = summary.get("videos_generated", 0)
                    result["total_candidates"] = summary.get("total_candidates", 0)
                    result["run_id"] = summary.get("run_id")
                results.append(result)
                print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        settings.BATCH_PHASE1_COUNT = old_phase1
        settings.BATCH_PHASE2_COUNT = old_phase2
        settings.BATCH_MULTI_VIDEO_ENABLE = old_multi
        settings.BATCH_TEST_MODE = old_test_mode

    print("=" * 60)
    print("all experiment results")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
