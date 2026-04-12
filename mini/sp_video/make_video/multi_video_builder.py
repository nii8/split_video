"""
multi_video_builder.py - 多视频合并构建器

用于将来自多个视频源的片段合并成一个视频文件。
"""

import os
import subprocess
import time
import sys
from datetime import datetime


def build_multi_video_filter_complex(sources, segments):
    """
    为多视频片段构建filter_complex字符串

    Args:
        sources: 视频源列表 [{"video_id": "...", "video_path": "..."}, ...]
        segments: 片段列表 [{"video_id": "...", "start": sec, "end": sec, "text": "..."}, ...]

    Returns:
        str: FFmpeg filter_complex 字符串
    """
    if not segments:
        raise ValueError("Segments list cannot be empty")

    # 创建视频源到索引的映射
    video_path_map = {src["video_id"]: src["video_path"] for src in sources}

    # 按照sources的顺序分配索引，确保相同video_id映射到相同的输入索引
    unique_video_ids = []
    for seg in segments:
        vid_id = seg["video_id"]
        if vid_id not in unique_video_ids and vid_id in video_path_map:
            unique_video_ids.append(vid_id)

    # 构建输入映射
    input_map = {vid_id: i for i, vid_id in enumerate(unique_video_ids)}

    filters = []
    stream_inputs = []

    for i, segment in enumerate(segments):
        video_id = segment["video_id"]
        start = segment["start"]
        end = segment["end"]

        if video_id not in input_map:
            print(f"[WARNING] Video ID {video_id} not found in sources, skipping segment", file=sys.stderr)
            continue

        input_idx = input_map[video_id]

        # Video trim and PTS adjustment
        filters.append(f"[{input_idx}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
        # Audio trim and PTS adjustment
        filters.append(f"[{input_idx}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];")
        # Add to concat inputs
        stream_inputs.extend([f"[v{i}]", f"[a{i}]"])

    if not stream_inputs:
        raise ValueError("No valid segments found for video building")

    n_segments = len(stream_inputs) // 2  # Each segment contributes 2 streams (video and audio)
    # Concatenate all segments
    concat_filters = f"{''.join(stream_inputs)}concat=n={n_segments}:v=1:a=1[outv][outa]"

    return "".join(filters) + concat_filters


def build_multi_video_command(sources, segments, output_path):
    """
    构建多视频合并的FFmpeg命令

    Args:
        sources: 视频源列表
        segments: 片段列表
        output_path: 输出路径

    Returns:
        tuple: (command_list, input_paths_list)
    """
    filter_complex = build_multi_video_filter_complex(sources, segments)

    # 构建输入路径列表
    video_path_map = {src["video_id"]: src["video_path"] for src in sources}
    unique_video_ids = []
    for seg in segments:
        vid_id = seg["video_id"]
        if vid_id not in unique_video_ids and vid_id in video_path_map:
            unique_video_ids.append(vid_id)

    input_paths = [video_path_map[vid_id] for vid_id in unique_video_ids if vid_id in video_path_map]

    cmd = ["ffmpeg"]
    for path in input_paths:
        cmd.extend(["-i", path])

    cmd.extend([
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
    ])

    return cmd, input_paths


def generate_multi_video(sources, segments, output_dir, candidate_id):
    """
    生成多视频输出文件

    Args:
        sources: 视频源列表 [{"video_id": "...", "video_path": "..."}, ...]
        segments: 片段列表 [{"video_id": "...", "start": sec, "end": sec, "text": "..."}, ...]
        output_dir: 输出目录
        candidate_id: 候选ID

    Returns:
        str: 输出文件路径
    """
    # 构建输出路径
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"multi_video_{candidate_id}.mp4")

    # 构建FFmpeg命令
    cmd, input_paths = build_multi_video_command(sources, segments, output_path)

    print(f"[MULTI-VIDEO] Building video from {len(input_paths)} sources", file=sys.stderr)
    print(f"[MULTI-VIDEO] Using {len(segments)} segments", file=sys.stderr)
    print(f"[MULTI-VIDEO] Command: {' '.join(cmd[:5])}... (truncated)", file=sys.stderr)

    try:
        # 执行FFmpeg命令
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"[MULTI-VIDEO] Successfully created: {output_path}", file=sys.stderr)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"[MULTI-VIDEO] Error occurred: {e}", file=sys.stderr)
        print(f"[MULTI-VIDEO] stderr: {e.stderr}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"[MULTI-VIDEO] Unexpected error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    # 测试用例
    sources = [
        {"video_id": "A001", "video_path": "/path/to/A001.mp4"},
        {"video_id": "B002", "video_path": "/path/to/B002.mp4"},
    ]

    segments = [
        {"video_id": "A001", "start": 0, "end": 10, "text": "第一个片段"},
        {"video_id": "B002", "start": 5, "end": 15, "text": "第二个片段"},
        {"video_id": "A001", "start": 20, "end": 30, "text": "第三个片段"},
    ]

    try:
        output_path = generate_multi_video(sources, segments, "./test_output", "test_001")
        print(f"Generated: {output_path}")
    except Exception as e:
        print(f"Failed to generate video: {e}")