import argparse
import json
import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import run_phase1_batch, run_phase2_batch, run_phase3
from make_video.step3 import cut_video_filter_complex, srt_time_to_seconds


def find_video_pairs(video_dir):
    pairs = []
    for name in sorted(os.listdir(video_dir)):
        if not name.lower().endswith(".srt"):
            continue
        video_id = os.path.splitext(name)[0]
        srt_path = os.path.join(video_dir, f"{video_id}.srt")
        mp4_path = os.path.join(video_dir, f"{video_id}.mp4")
        if not os.path.exists(mp4_path):
            raise FileNotFoundError(f"未找到同名视频文件: {mp4_path}")
        pairs.append((video_id, srt_path, mp4_path))
    return pairs


def keep_intervals_to_segments(keep_intervals):
    segments = []
    for interval in keep_intervals:
        start, end = interval[0]
        if not start or not end:
            continue
        start_sec = srt_time_to_seconds(start)
        end_sec = srt_time_to_seconds(end)
        if end_sec <= start_sec:
            continue
        segments.append((start_sec, end_sec))
    return segments


def get_total_duration(segments):
    return round(sum(end - start for start, end in segments), 3)


def process_single_video(video_id, srt_path, mp4_path, output_root, force=False):
    video_output_dir = os.path.join(output_root, video_id)
    os.makedirs(video_output_dir, exist_ok=True)

    output_video_path = os.path.join(video_output_dir, f"{video_id}_5min.mp4")
    summary_path = os.path.join(video_output_dir, "summary.json")

    if os.path.exists(output_video_path) and not force:
        print(f"[SKIP] {video_id}: 已存在输出视频 {output_video_path}")
        return {
            "video_id": video_id,
            "status": "skipped",
            "output_video": output_video_path,
        }

    print(f"\n{'=' * 80}")
    print(f"[START] {video_id}")
    print(f"srt={srt_path}")
    print(f"mp4={mp4_path}")
    print(f"out={video_output_dir}")
    print(f"{'=' * 80}")

    t1 = time.time()

    step1_path = os.path.join(video_output_dir, "step1.txt")
    step2_path = os.path.join(video_output_dir, "step2.txt")

    phase1_result = run_phase1_batch(video_id, srt_path, step1_path)
    phase2_result = run_phase2_batch(video_id, phase1_result, step2_path)
    keep_intervals = run_phase3(srt_path, phase2_result, video_output_dir)

    segments = keep_intervals_to_segments(keep_intervals)
    if not segments:
        raise ValueError(f"{video_id} 未生成任何有效时间片段")

    total_duration = get_total_duration(segments)
    print(f"[INFO] {video_id}: {len(segments)} 个片段，合计 {total_duration} 秒")

    cut_video_filter_complex(mp4_path, output_video_path, segments)

    summary = {
        "video_id": video_id,
        "srt_path": srt_path,
        "mp4_path": mp4_path,
        "output_video": output_video_path,
        "segment_count": len(segments),
        "selected_duration_sec": total_duration,
        "intervals_path": os.path.join(video_output_dir, "intervals.json"),
        "step1_path": step1_path,
        "step2_path": step2_path,
        "status": "success",
        "elapsed_sec": round(time.time() - t1, 2),
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"[DONE] {video_id}: {output_video_path}")
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="批量生成单视频5分钟版本")
    parser.add_argument(
        "--video_dir",
        default=os.path.join("data", "video"),
        help="输入目录，包含同名 mp4 和 srt",
    )
    parser.add_argument(
        "--output_dir",
        default=os.path.join("data", "output_5min"),
        help="输出目录，不覆盖原视频",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="如果输出已存在则覆盖重跑",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    video_pairs = find_video_pairs(args.video_dir)
    if not video_pairs:
        raise ValueError(f"目录下未找到可处理的视频对: {args.video_dir}")

    print(f"[INIT] 共发现 {len(video_pairs)} 个视频")

    results = []
    for video_id, srt_path, mp4_path in video_pairs:
        try:
            result = process_single_video(
                video_id,
                srt_path,
                mp4_path,
                args.output_dir,
                force=args.force,
            )
        except Exception as e:
            result = {
                "video_id": video_id,
                "status": "error",
                "error": str(e),
            }
            print(f"[ERROR] {video_id}: {e}")
        results.append(result)

    summary_path = os.path.join(args.output_dir, "batch_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    success_count = len([item for item in results if item.get("status") == "success"])
    error_count = len([item for item in results if item.get("status") == "error"])
    skipped_count = len([item for item in results if item.get("status") == "skipped"])

    print("\n" + "=" * 80)
    print("[SUMMARY]")
    print(f"success={success_count} error={error_count} skipped={skipped_count}")
    print(f"batch_summary={summary_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
