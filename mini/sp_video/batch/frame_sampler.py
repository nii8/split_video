"""
第一阶段：抽帧。

这里只做一件事：
给定视频路径和时间段，按固定间隔抽 9 张图左右出来。

这里故意写得很直，不做复杂抽象。
后续运行环境如果 ffmpeg 路径不同，直接改 sample_frames_for_interval() 里的命令即可。
"""

import os
import subprocess
import time


def srt_time_to_seconds(time_str):
    """把 SRT 时间格式转成秒"""
    h, m, s_ms = time_str.split(":")
    s, ms = s_ms.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def build_sample_timestamps(start_sec, end_sec, sample_every_sec=2, max_frames=9):
    """根据时间范围生成抽帧时间点"""
    timestamps = []
    if end_sec <= start_sec:
        return timestamps

    cur = start_sec
    while cur < end_sec and len(timestamps) < max_frames:
        timestamps.append(round(cur, 3))
        cur += sample_every_sec

    if not timestamps:
        timestamps.append(round(start_sec, 3))
    return timestamps


def sample_frames_for_interval(video_path, start_sec, end_sec, sample_every_sec=2, output_dir=None, max_frames_per_interval=9):
    """对单个时间段抽帧，返回图片路径列表"""
    if output_dir is None:
        output_dir = "."
    os.makedirs(output_dir, exist_ok=True)

    timestamps = build_sample_timestamps(start_sec, end_sec, sample_every_sec, max_frames_per_interval)
    image_paths = []
    ffmpeg_duration_sec = 0.0

    for i, ts in enumerate(timestamps):
        output_path = os.path.join(output_dir, f"frame_{i + 1:03d}.jpg")
        # 这里直接用最朴素的 ffmpeg 单帧截图命令。
        # 如果后续环境里 ffmpeg 命令名不同，改这里就够了。
        cmd = [
            "ffmpeg",
            "-ss", str(ts),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            "-y",
            output_path,
        ]
        start = time.time()
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        ffmpeg_duration_sec += time.time() - start
        if os.path.exists(output_path):
            image_paths.append(output_path)

    return {
        "image_paths": image_paths,
        "ffmpeg_duration_sec": round(ffmpeg_duration_sec, 2),
    }


def sample_frames_for_intervals(video_path, intervals, output_dir=None, sample_every_sec=2, max_frames_per_interval=9):
    """对多个 intervals 批量抽帧，返回按 interval 分组的图片路径"""
    if output_dir is None:
        output_dir = "."
    os.makedirs(output_dir, exist_ok=True)

    grouped = []
    for idx, item in enumerate(intervals):
        start_time, end_time = item[0]
        if not start_time or not end_time:
            continue

        interval_dir = os.path.join(output_dir, f"interval_{idx + 1:03d}")
        start_sec = srt_time_to_seconds(start_time)
        end_sec = srt_time_to_seconds(end_time)
        sample_result = sample_frames_for_interval(
            video_path,
            start_sec,
            end_sec,
            sample_every_sec=sample_every_sec,
            output_dir=interval_dir,
            max_frames_per_interval=max_frames_per_interval,
        )
        grouped.append({
            "interval_index": idx + 1,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "image_paths": sample_result["image_paths"],
            "ffmpeg_duration_sec": sample_result["ffmpeg_duration_sec"],
        })

    return grouped
