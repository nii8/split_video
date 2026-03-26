import os
import subprocess
import time
from datetime import datetime
import sys
import bisect
import settings


def extract_keyframes(video_file):
    """提取视频中的所有关键帧时间点"""
    try:
        cmd = [
            "ffprobe",
            "-select_streams",
            "v",
            "-show_frames",
            "-show_entries",
            "frame=pict_type,pts_time",
            "-of",
            "csv=p=0",
            video_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        keyframes = []
        for line in result.stdout.strip().split("\n"):
            if ",I," in line or line.endswith(",I"):
                parts = line.split(",")
                for part in parts:
                    if part.replace(".", "").replace("-", "").isdigit() or part.replace(
                        ".", ""
                    ).startswith("-"):
                        try:
                            pts = float(part)
                            if pts >= 0:
                                keyframes.append(pts)
                        except ValueError:
                            continue
        keyframes.sort()
        return keyframes
    except Exception as e:
        print(f"[KEYFRAME] extract failed: {e}", file=sys.stderr)
        return []


def find_nearest_keyframe_before(keyframes, target_time):
    """使用二分查找找到 target_time 之前的最近关键帧"""
    if not keyframes:
        return None
    idx = bisect.bisect_right(keyframes, target_time)
    if idx == 0:
        return None
    return keyframes[idx - 1]


def probe_video_duration(video_file):
    """使用 ffprobe 获取视频精确时长"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            video_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return None


def log_clip_info(
    clip_idx,
    start,
    end,
    expected_duration,
    actual_duration,
    accumulated_offset,
    mode,
    kf_delta,
    kf_at,
):
    """记录片段切割日志到 stderr"""
    offset_str = (
        f"+{accumulated_offset:.2f}s"
        if accumulated_offset >= 0
        else f"{accumulated_offset:.2f}s"
    )
    kf_delta_str = f"{kf_delta:.2f}s" if kf_delta != float("inf") else "N/A"
    kf_at_str = f"{kf_at:.2f}s" if kf_at is not None else "N/A"
    print(
        f"[CLIP {clip_idx}] start={start:.1f}s end={end:.1f}s "
        f"expected={expected_duration:.1f}s actual={actual_duration:.1f}s "
        f"offset={offset_str} mode={mode} kf_delta={kf_delta_str} kf_at={kf_at_str}",
        file=sys.stderr,
    )


def extract_audio(input_file):
    print("extract_audio", input_file)
    if os.path.exists(input_file.replace("mp4", "wav")):
        return
    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-vn",
        "-acodec",
        "pcm_s16le",
        input_file.replace("mp4", "wav"),
    ]
    print(cmd)
    subprocess.run(cmd)


def cut_and_merge_audio(input_audio, user_stamp, keep_intervals):
    dir_name = os.path.dirname(input_audio)
    base_name = os.path.basename(input_audio)
    input_audio_file = os.path.join(dir_name, f"{base_name}")
    output_audio = os.path.join(
        dir_name, f"{base_name.replace('.wav', '')}_{user_stamp}.wav"
    )
    os.makedirs("wav", exist_ok=True)
    temp_files = []
    try:
        for i, (start, end) in enumerate(keep_intervals):
            temp_file = f"./wav/temp_audio_{i}.wav"
            temp_files.append(temp_file)
            cmd = [
                "ffmpeg",
                "-i",
                input_audio_file,
                "-ss",
                str(start),
                "-to",
                str(end),
                "-c:a",
                "pcm_s16le",
                "-y",
                temp_file,
            ]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)

        with open("concat_list.txt", "w") as f:
            for file in temp_files:
                f.write(f"file '{os.path.abspath(file)}'\n")
        cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            "concat_list.txt",
            "-c:a",
            "pcm_s16le",
            "-y",
            output_audio,
        ]
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
        return output_audio
    finally:
        for file in temp_files:
            if os.path.exists(file):
                os.remove(file)
        if os.path.exists("concat_list.txt"):
            os.remove("concat_list.txt")


def float_to_time_str(seconds_float):
    hours = int(seconds_float // 3600)
    minutes = int((seconds_float % 3600) // 60)
    seconds = seconds_float % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


def cut_and_merge_video_img(
    video_file, user_stamp, keep_intervals, video_id, keyframes=None
):
    """
    切割并合并视频片段。

    注意：ffmpeg concat demuxer 不支持 inpoint/outpoint 参数，
    所以先用 -ss 和 -to 切割每个片段，再合并。

    keyframes: 关键帧时间列表，用于智能选择 copy 或重编码模式
    """
    if keyframes is None:
        keyframes = []

    output_video = f"{video_file.replace('.mp4', '')}_{user_stamp}.mp4"
    temp_files = []
    clip_list_file = f"clip_list_{video_id}.txt"

    accumulated_offset = 0.0
    copy_count = 0
    reencode_count = 0

    try:
        for i, (start, end) in enumerate(keep_intervals):
            temp_file = f"./temp_video_{video_id}_{i}.mp4"
            temp_files.append(temp_file)
            expected_duration = end - start

            kf_before = (
                find_nearest_keyframe_before(keyframes, start) if keyframes else None
            )
            delta = start - kf_before if kf_before is not None else float("inf")

            if delta < settings.KEYFRAME_THRESHOLD and kf_before is not None:
                actual_start = kf_before + accumulated_offset
                mode = "copy"
                codec_params = ["-c:v", "copy", "-c:a", "copy"]
            else:
                actual_start = start + accumulated_offset
                mode = "reencode"
                codec_params = [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-c:a",
                    "copy",
                ]

            cmd = (
                [
                    "ffmpeg",
                    "-ss",
                    str(actual_start),
                    "-i",
                    video_file,
                    "-t",
                    str(expected_duration),
                ]
                + codec_params
                + ["-y", temp_file]
            )
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)

            actual_duration = probe_video_duration(temp_file)
            if actual_duration is not None:
                offset_delta = actual_duration - expected_duration
                accumulated_offset += offset_delta
            else:
                actual_duration = expected_duration

            if mode == "copy":
                copy_count += 1
            else:
                reencode_count += 1

            log_clip_info(
                i,
                start,
                end,
                expected_duration,
                actual_duration,
                accumulated_offset,
                mode,
                delta,
                kf_before,
            )

        offset_str = (
            f"+{accumulated_offset:.2f}s"
            if accumulated_offset >= 0
            else f"{accumulated_offset:.2f}s"
        )
        print(
            f"[SUMMARY] total_clips={len(keep_intervals)} copy={copy_count} reencode={reencode_count} final_offset={offset_str}",
            file=sys.stderr,
        )

        # Step 2: 用 concat demuxer 合并所有片段（不需要 inpoint/outpoint）
        with open(clip_list_file, "w") as f:
            for file in temp_files:
                f.write(f"file '{os.path.abspath(file)}'\n")

        cmd_concat = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            clip_list_file,
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-y",
            output_video,
        ]
        subprocess.run(cmd_concat, check=True, stderr=subprocess.DEVNULL)

    except subprocess.CalledProcessError as e:
        print(f"视频处理过程中出错：{e}")
        raise
    finally:
        # 清理临时文件
        for file in temp_files:
            if os.path.exists(file):
                os.remove(file)
        if os.path.exists(clip_list_file):
            os.remove(clip_list_file)

    return output_video


def time_str_to_seconds(time_str):
    time_str = time_str.replace(",", ".")
    hh_mm_ss, milliseconds = time_str.split(".")
    hh, mm, ss = hh_mm_ss.split(":")
    total_seconds = int(hh) * 3600 + int(mm) * 60 + float(f"{ss}.{milliseconds}")
    return round(total_seconds, 3)


def ffmpeg_cut_mp4(keep_intervals_list, video_path, video_id, user_id):
    input_video_file = video_path
    timestamp = datetime.now().strftime("%m%d_%H%M")
    keep_intervals = []
    for unit in keep_intervals_list:
        cut_start, cut_end = unit[0][0], unit[0][1]
        print(cut_start, cut_end, unit[1])
        keep_intervals.append(
            [time_str_to_seconds(cut_start), time_str_to_seconds(cut_end)]
        )

    print(f"[KEYFRAME] extracting from {input_video_file}", file=sys.stderr)
    keyframes = extract_keyframes(input_video_file)
    print(f"[KEYFRAME] found {len(keyframes)} keyframes", file=sys.stderr)

    input_audio = input_video_file.replace("mp4", "wav")
    user_stamp = f"{user_id}_{timestamp}"
    output_audio = cut_and_merge_audio(input_audio, user_stamp, keep_intervals)
    output_video = cut_and_merge_video_img(
        input_video_file, user_stamp, keep_intervals, video_id, keyframes
    )

    print(f"output_audio={output_audio}")
    print(f"output_video={output_video}")
    dir_name = os.path.dirname(input_video_file)
    base_name = os.path.basename(input_video_file)
    out_stamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    output_video_path = os.path.join(
        dir_name, f"{base_name.replace('.mp4', '')}_{user_id}_{out_stamp}.mp4"
    )
    merge_cmd = [
        "ffmpeg",
        "-i",
        output_video,
        "-i",
        output_audio,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        "-strict",
        "experimental",
        "-y",
        output_video_path,
    ]
    print(f"merge_cmd={merge_cmd}")
    try:
        subprocess.run(merge_cmd, check=True)
    finally:
        for f in [output_video, output_audio]:
            if f and os.path.exists(f):
                os.remove(f)
    return output_video_path


def cut_video_main(keep_intervals, video_path, video_id, user_id):
    t1 = time.time()
    extract_audio(video_path)
    output_video_path = ffmpeg_cut_mp4(keep_intervals, video_path, video_id, user_id)
    t2 = time.time()
    print(f"cost {round(t2 - t1, 2)} s")
    return output_video_path
