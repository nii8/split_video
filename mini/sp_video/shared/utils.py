import json
import os
from datetime import datetime

from make_video.step3 import srt_time_to_seconds


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def make_run_id():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


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


def classify_duration_status(total_duration, target_min_sec, target_max_sec):
    if total_duration < target_min_sec:
        return "too_short"
    if total_duration > target_max_sec:
        return "too_long"
    return "ok"


def snapshot_prompts(run_dir, data):
    prompt_path = os.path.join(run_dir, "prompt_snapshot.json")
    with open(prompt_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return prompt_path

