import argparse
import json
import os
import sys
import time
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from phase1_select.prompts import PROMPT_SHORT as PHASE1_PROMPT
from phase1_select.runner import run_phase1 as _run_phase1
from phase2_rewrite.prompts import PROMPT_SHORT as PHASE2_PROMPT
from phase2_rewrite.runner import run_phase2 as _run_phase2
from phase3_match.runner import run_phase3
from phase4_cut.runner import cut_video_filter_complex, srt_time_to_seconds
from shared.logger import BatchLogger
from shared.output import error, info, warn


DEFAULT_OUTPUT_DIR = os.path.join("data", "output_short")
DEFAULT_LOG_ROOT = os.path.join("data", "run_logs", "single_video_short")
TARGET_MIN_SEC = 60
TARGET_MAX_SEC = 150
TARGET_SEC = 90


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def make_run_id():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_phase1_batch(srt_path, output_path):
    return _run_phase1(srt_path, prompt=PHASE1_PROMPT, output_path=output_path)


def run_phase2_batch(phase1_content, output_path):
    return _run_phase2(phase1_content, prompt=PHASE2_PROMPT, output_path=output_path)


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


def get_srt_duration_sec(srt_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    time_lines = [line.strip() for line in lines if "-->" in line]
    if not time_lines:
        return 0.0
    start_text = time_lines[0].split(" --> ")[0].strip()
    end_text = time_lines[-1].split(" --> ")[1].strip()
    return round(max(0.0, srt_time_to_seconds(end_text) - srt_time_to_seconds(start_text)), 3)


def count_timeline_entries(text):
    return sum(1 for line in text.splitlines() if "-->" in line)


def classify_duration_status(total_duration):
    if total_duration < TARGET_MIN_SEC:
        return "too_short"
    if total_duration > TARGET_MAX_SEC:
        return "too_long"
    return "ok"


def snapshot_prompts(run_dir):
    prompt_path = os.path.join(run_dir, "prompt_snapshot.json")
    with open(prompt_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "phase1_prompt": PHASE1_PROMPT,
                "phase2_prompt": PHASE2_PROMPT,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    return prompt_path


def process_single_video(video_id, srt_path, mp4_path, output_root, logger, force=False):
    video_output_dir = os.path.join(output_root, video_id)
    os.makedirs(video_output_dir, exist_ok=True)

    output_video_path = os.path.join(video_output_dir, f"{video_id}_short.mp4")
    summary_path = os.path.join(video_output_dir, "summary.json")

    if os.path.exists(output_video_path) and not force:
        warn(f"[SKIP] {video_id}: 已存在输出视频 {output_video_path}")
        return {
            "video_id": video_id,
            "status": "skipped",
            "output_video": output_video_path,
        }

    info("=" * 80)
    info(f"[START] {video_id}")
    info(f"srt={srt_path}")
    info(f"mp4={mp4_path}")
    info(f"out={video_output_dir}")
    info("=" * 80)

    t1 = time.time()
    original_duration_sec = get_srt_duration_sec(srt_path)
    logger.log_event(
        "video_start",
        video_id=video_id,
        srt_path=srt_path,
        mp4_path=mp4_path,
        output_dir=video_output_dir,
        original_duration_sec=original_duration_sec,
        version="short",
    )

    step1_path = os.path.join(video_output_dir, "step1.txt")
    step2_path = os.path.join(video_output_dir, "step2.txt")

    phase1_start = time.time()
    phase1_result = run_phase1_batch(srt_path, step1_path)
    phase1_duration = time.time() - phase1_start
    step1_count = count_timeline_entries(phase1_result)
    logger.log_phase(video_id, "phase1", 1, phase1_duration, "success", selected_count=step1_count, output_path=step1_path, version="short")

    phase2_start = time.time()
    phase2_result = run_phase2_batch(phase1_result, step2_path)
    phase2_duration = time.time() - phase2_start
    step2_count = count_timeline_entries(phase2_result)
    logger.log_phase(video_id, "phase2", 1, phase2_duration, "success", selected_count=step2_count, output_path=step2_path, version="short")

    phase3_start = time.time()
    keep_intervals = run_phase3(srt_path, phase2_result, video_output_dir)
    phase3_duration = time.time() - phase3_start

    segments = keep_intervals_to_segments(keep_intervals)
    if not segments:
        logger.log_phase(video_id, "phase3", 1, phase3_duration, "failed", reason="未生成任何有效时间片段", version="short")
        raise ValueError(f"{video_id} 未生成任何有效时间片段")

    total_duration = get_total_duration(segments)
    duration_status = classify_duration_status(total_duration)
    compression_ratio = round(total_duration / original_duration_sec, 4) if original_duration_sec > 0 else None
    logger.log_phase(
        video_id,
        "phase3",
        1,
        phase3_duration,
        "success",
        matched=len(keep_intervals),
        selected_duration_sec=total_duration,
        duration_status=duration_status,
        original_duration_sec=original_duration_sec,
        compression_ratio=compression_ratio,
        output_path=os.path.join(video_output_dir, "intervals.json"),
        version="short",
    )
    info(f"{video_id}: 原始 {original_duration_sec} 秒 -> 保留 {total_duration} 秒，{len(segments)} 个片段，status={duration_status}")

    phase4_start = time.time()
    cut_video_filter_complex(mp4_path, output_video_path, segments)
    phase4_duration = time.time() - phase4_start
    logger.log_phase(video_id, "phase4", 1, phase4_duration, "success", output_path=output_video_path, selected_duration_sec=total_duration, version="short")

    summary = {
        "video_id": video_id,
        "srt_path": srt_path,
        "mp4_path": mp4_path,
        "output_video": output_video_path,
        "original_duration_sec": original_duration_sec,
        "segment_count": len(segments),
        "selected_duration_sec": total_duration,
        "compression_ratio": compression_ratio,
        "duration_target_sec": TARGET_SEC,
        "duration_status": duration_status,
        "step1_count": step1_count,
        "step2_count": step2_count,
        "intervals_path": os.path.join(video_output_dir, "intervals.json"),
        "step1_path": step1_path,
        "step2_path": step2_path,
        "status": "success",
        "elapsed_sec": round(time.time() - t1, 2),
        "version": "short",
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.log_event("video_done", **summary)
    info(f"[DONE] {video_id}: {output_video_path}")
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="批量生成单视频短精华版本")
    parser.add_argument("--video_dir", default=os.path.join("data", "video"), help="输入目录，包含同名 mp4 和 srt")
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR, help="输出目录，不覆盖原视频")
    parser.add_argument("--force", action="store_true", help="如果输出已存在则覆盖重跑")
    parser.add_argument("--log_root", default=DEFAULT_LOG_ROOT, help="按次归档日志目录，每次运行会新建子目录")
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    ensure_dir(args.log_root)

    run_id = make_run_id()
    run_log_dir = ensure_dir(os.path.join(args.log_root, run_id))
    text_log_path = os.path.join(run_log_dir, "run.log")
    jsonl_log_path = os.path.join(run_log_dir, "events.jsonl")
    prompt_snapshot_path = snapshot_prompts(run_log_dir)

    logger = BatchLogger(jsonl_log_path)
    logger.log_event("run_start", run_id=run_id, video_dir=args.video_dir, output_dir=args.output_dir, log_dir=run_log_dir, prompt_snapshot=prompt_snapshot_path, version="short")

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    log_fp = open(text_log_path, "a", encoding="utf-8")
    sys.stdout = TeeStream(original_stdout, log_fp)
    sys.stderr = TeeStream(original_stderr, log_fp)

    try:
        video_pairs = find_video_pairs(args.video_dir)
        if not video_pairs:
            raise ValueError(f"目录下未找到可处理的视频对: {args.video_dir}")

        info(f"[INIT] 共发现 {len(video_pairs)} 个视频")
        info(f"[LOG] run_id={run_id}")
        info(f"[LOG] text_log={text_log_path}")
        info(f"[LOG] events_jsonl={jsonl_log_path}")
        info(f"[LOG] prompt_snapshot={prompt_snapshot_path}")

        results = []
        run_start = time.time()
        for video_id, srt_path, mp4_path in video_pairs:
            try:
                result = process_single_video(video_id, srt_path, mp4_path, args.output_dir, logger, force=args.force)
            except Exception as e:
                result = {"video_id": video_id, "status": "error", "error": str(e), "version": "short"}
                logger.log_event("video_error", video_id=video_id, error=str(e), version="short")
                error(f"{video_id}: {e}")
            results.append(result)

        summary_path = os.path.join(args.output_dir, "batch_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        success_count = len([item for item in results if item.get("status") == "success"])
        error_count = len([item for item in results if item.get("status") == "error"])
        skipped_count = len([item for item in results if item.get("status") == "skipped"])
        too_short_count = len([item for item in results if item.get("duration_status") == "too_short"])
        too_long_count = len([item for item in results if item.get("duration_status") == "too_long"])

        run_summary = {
            "run_id": run_id,
            "video_dir": args.video_dir,
            "output_dir": args.output_dir,
            "log_dir": run_log_dir,
            "text_log": text_log_path,
            "events_jsonl": jsonl_log_path,
            "prompt_snapshot": prompt_snapshot_path,
            "video_count": len(video_pairs),
            "success_count": success_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "too_short_count": too_short_count,
            "too_long_count": too_long_count,
            "elapsed_sec": round(time.time() - run_start, 2),
            "batch_summary_path": summary_path,
            "version": "short",
        }
        run_summary_path = os.path.join(run_log_dir, "run_summary.json")
        with open(run_summary_path, "w", encoding="utf-8") as f:
            json.dump(run_summary, f, ensure_ascii=False, indent=2)

        logger.log_event("run_done", **run_summary)

        info("=" * 80)
        info("[SUMMARY]")
        info(f"success={success_count} error={error_count} skipped={skipped_count}")
        info(f"too_short={too_short_count} too_long={too_long_count}")
        info(f"batch_summary={summary_path}")
        info(f"run_summary={run_summary_path}")
        info("=" * 80)
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        log_fp.close()


if __name__ == "__main__":
    main()
