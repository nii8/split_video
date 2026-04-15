import argparse
import json
import os
import sys
import time
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from openai import OpenAI

import settings
from batch.logger import BatchLogger
from batch.output import error, info, warn
from make_time.step2 import get_keep_intervals
from make_video.step3 import cut_video_filter_complex, srt_time_to_seconds


PHASE1_PROMPT = """核心指令： 请你担任一位短视频素材筛选员，严格遵守以下原则：
1.零创作原则： 你输出的每一个句子片段，必须原封不动、一字不差地来自附件字幕文件。严禁任何形式的改写、概括、提炼或拼接。
2.时间轴对应原则： 每个筛选出的句子片段都必须附带其原始的精确时间轴。

你的任务：
仔细阅读附件字幕文件的全部内容。
从中筛选出符合以下特质的原始句子片段：
1.最具冲击力、颠覆性的句子。
2.最核心、点明主题的句子。
3.最吸引人、能制造悬念的句子。
4.最能引发情感共鸣或冲突的句子。
5.最能推进原叙事、原论述向前发展的句子。

筛选时额外遵守以下约束：
1.这次目标是做高密度短精华版，因此素材宁可精，不要贪多。
2.优先删除寒暄、客套、口头禅、重复表达、空泛感慨、无信息增量的铺垫。
3.优先保留观点、结论、关键解释、转折、冲突、案例、方法、结果。
4.尽量保留单句就能成立、且能和前后内容自然衔接的句子。

输出时，仅需列出筛选出的句子及其对应时间轴，无需进行任何顺序调整或组合。
输出格式要求：
请按以下格式输出，严格保持每行结构清晰：

(原始时间轴) --> (原始时间轴)
(完全摘自附件的原始文案)
"""


PHASE2_PROMPT = """核心指令： 请你担任一位短视频脚本架构师。
严格遵守以下原则：
1.零创作原则： 你输出的每一个句子片段，必须原封不动、一字不差地来自附件字幕文件。严禁任何形式的改写、概括、提炼或拼接。
2.时间轴对应原则： 每个筛选出的句子片段都必须附带其原始的精确时间轴。
3.顺序原则： 你必须严格遵守原字幕的时间顺序组织脚本，原则上禁止调换顺序，禁止把后面的内容提前到前面。

你的任务：
根据提供的筛选句子片段库为唯一素材来源（即一系列带有时间轴的原始句子片段）。
重组与排序： 将这些原始句子片段，在不改变原时间顺序的前提下进行删减和组织，形成一个紧凑、有节奏、有情绪起伏的脚本。

叙事逻辑：
a. 黄金3秒钩子： 使用素材库中最具颠覆性、悬念或共鸣的句子开头。
b. 中间情绪推进： 围绕核心主题，从素材库中选择体现冲突、转折、感悟的句子，组合成有推进感的故事线。
c. 结尾升华或互动： 用素材库中一句有力量、引人深思或引发共鸣的句子收尾。

严格遵守红线： 脚本中的每一句话都必须源自提供的素材库，且时间轴与文案严格对应，严禁任何创作或修改。
这次脚本目标是高密度短精华版，请主动压缩冗余内容，优先删除重复铺垫、冗长过渡、相近意思的重复句、无实质推进的话。
你的工作重点是做短精华，不是做接近 5 分钟的保真压缩版。

输出格式要求：
请按以下格式输出最终脚本：

(原始时间轴) --> (原始时间轴)
(完全摘自附件的原始文案)

筛选句子片段库：
"""


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


def call_llm_batch(prompt):
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
    info(f"[LLM] batch call duration: {round(time.time() - start, 2)} s")
    return response.choices[0].message.content


def run_phase1_batch(srt_path, output_path):
    srt_content = open(srt_path, "r", encoding="utf-8").read()
    result = call_llm_batch(PHASE1_PROMPT + "\n\n" + srt_content)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return result


def run_phase2_batch(phase1_content, output_path):
    result = call_llm_batch(PHASE2_PROMPT + "\n" + phase1_content)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return result


def run_phase3(srt_path, script, output_dir=None):
    intervals_path = os.path.join(output_dir, "intervals.json") if output_dir else None
    result = get_keep_intervals(srt_path, script)
    keep_intervals = result.get("keep_intervals", [])
    valid = [item for item in keep_intervals if item[0][0]]
    if intervals_path:
        with open(intervals_path, "w", encoding="utf-8") as f:
            json.dump(valid, f, ensure_ascii=False, indent=2)
    return valid


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
