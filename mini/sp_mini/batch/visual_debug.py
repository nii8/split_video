"""
调试第一阶段视觉评分。

这个脚本依赖项目里的 settings.py。
适合在完整运行环境里，单独拿一个时间段做抽帧、拼图、评分测试。
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from batch.visual_scorer import score_interval_visual


def main():
    parser = argparse.ArgumentParser(description="单独调试第一阶段视觉评分")
    parser.add_argument("--video_id", required=True)
    parser.add_argument("--video_path", required=True)
    parser.add_argument("--start", required=True, help="SRT 格式起始时间，如 00:00:10,000")
    parser.add_argument("--end", required=True, help="SRT 格式结束时间，如 00:00:28,000")
    parser.add_argument("--work_dir", default="./data/batch_results/visual_debug")
    parser.add_argument("--use_llm", action="store_true")
    args = parser.parse_args()

    interval_item = [(args.start, args.end), "debug interval"]
    result = score_interval_visual(
        args.video_id,
        "debug_candidate",
        args.video_path,
        interval_item,
        os.path.join(args.work_dir, args.video_id),
        use_llm=args.use_llm,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
