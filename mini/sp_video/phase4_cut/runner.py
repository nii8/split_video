import os
import time

from make_video.step3 import cut_video_filter_complex, cut_video_main, srt_time_to_seconds


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


def cut_video(mp4_path, output_path, keep_intervals=None, segments=None):
    if segments is None:
        segments = keep_intervals_to_segments(keep_intervals or [])
    if not segments:
        raise ValueError("No valid intervals provided for video cutting")
    return cut_video_filter_complex(mp4_path, output_path, segments)


def run_phase4(video_path, keep_intervals, video_id):
    phase_start = time.time()
    print(f"[Stage 4] 开始剪辑，共 {len(keep_intervals)} 个片段 ...")
    output_path = cut_video_main(keep_intervals, video_path, video_id, "cli")
    print(f"[Stage 4] 视频已生成: {output_path}")
    print(f"[Stage 4] duration: {round(time.time() - phase_start, 2)} s")
    return output_path

