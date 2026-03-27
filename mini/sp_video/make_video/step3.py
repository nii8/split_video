import os
import subprocess
import time
from datetime import datetime
import sys
import bisect
import settings


def srt_time_to_seconds(srt_time):
    """
    Convert SRT time format to seconds.

    Args:
        srt_time (str): SRT time format string like "00:01:23,456"

    Returns:
        float: Time in seconds like 83.456
    """
    time_parts = srt_time.replace(",", ".").split(":")
    hours = int(time_parts[0])
    minutes = int(time_parts[1])
    seconds_milliseconds = float(time_parts[2])

    return hours * 3600 + minutes * 60 + seconds_milliseconds


def cut_video_filter_complex(input_path, output_path, segments):
    """
    Cut video using filter_complex to trim and concatenate segments.

    Args:
        input_path (str): Input video path
        output_path (str): Output video path
        segments (list): List of (start_sec, end_sec) tuples

    Raises:
        Exception: Re-raises any subprocess errors
    """
    from .filter_builder import build_filter_complex

    filter_complex = build_filter_complex(segments)

    cmd = [
        "ffmpeg",
        "-i",
        input_path,
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-y",
        output_path,
    ]

    try:
        print(
            f"[FFMPEG] Executing: {' '.join(cmd[:5])}... (truncated for readability)",
            file=sys.stderr,
        )
        subprocess.run(cmd, check=True)
        print(f"[FFMPEG] Completed successfully: {output_path}", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"[FFMPEG] Error occurred: {e}", file=sys.stderr)
        raise


def float_to_time_str(seconds_float):
    hours = int(seconds_float // 3600)
    minutes = int((seconds_float % 3600) // 60)
    seconds = seconds_float % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


def time_str_to_seconds(time_str):
    time_str = time_str.replace(",", ".")
    hh_mm_ss, milliseconds = time_str.split(".")
    hh, mm, ss = hh_mm_ss.split(":")
    total_seconds = int(hh) * 3600 + int(mm) * 60 + float(f"{ss}.{milliseconds}")
    return round(total_seconds, 3)


def cut_video_main(keep_intervals, video_path, video_id, user_id):
    t1 = time.time()
    print(
        f"[CUT_VIDEO_MAIN] Starting video cut for video_id: {video_id}, user_id: {user_id}",
        file=sys.stderr,
    )

    # Filter out invalid intervals where interval[0] is (None, None)
    valid_intervals = [
        (interval[0][0], interval[0][1])
        for interval in keep_intervals
        if interval[0][0] is not None
    ]

    if not valid_intervals:
        print("[CUT_VIDEO_MAIN] No valid intervals to process", file=sys.stderr)
        # Handle empty list case - return original video path or raise exception
        raise ValueError("No valid intervals provided for video cutting")

    # Convert SRT formatted times to seconds
    segments = [
        (srt_time_to_seconds(start), srt_time_to_seconds(end))
        for start, end in valid_intervals
    ]

    import os

    # Build output path: data/hanbing/{video_id}/output.mp4
    output_dir = os.path.join("data", "hanbing", str(video_id))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "output.mp4")

    # Call the new filter complex function
    cut_video_filter_complex(video_path, output_path, segments)

    t2 = time.time()
    print(
        f"[CUT_VIDEO_MAIN] Completed in {round(t2 - t1, 2)} s, output: {output_path}",
        file=sys.stderr,
    )
    return output_path
