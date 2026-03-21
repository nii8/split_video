import os
import subprocess
import time
from datetime import datetime


def extract_audio(input_file):
    print('extract_audio', input_file)
    if os.path.exists(input_file.replace('mp4', 'wav')):
        return
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-vn",
        "-acodec", "pcm_s16le",
        input_file.replace('mp4', 'wav')
    ]
    print(cmd)
    subprocess.run(cmd)


def cut_and_merge_audio(input_audio, user_stamp, keep_intervals):
    dir_name = os.path.dirname(input_audio)
    base_name = os.path.basename(input_audio)
    input_audio_file = os.path.join(dir_name, f"{base_name}")
    output_audio = os.path.join(dir_name, f"{base_name.replace('.wav', '')}_{user_stamp}.wav")
    os.makedirs('wav', exist_ok=True)
    temp_files = []
    try:
        for i, (start, end) in enumerate(keep_intervals):
            temp_file = f"./wav/temp_audio_{i}.wav"
            temp_files.append(temp_file)
            cmd = [
                "ffmpeg",
                "-i", input_audio_file,
                "-ss", str(start),
                "-to", str(end),
                "-c:a", "pcm_s16le",
                "-y",
                temp_file
            ]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)

        with open("concat_list.txt", "w") as f:
            for file in temp_files:
                f.write(f"file '{os.path.abspath(file)}'\n")
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", "concat_list.txt",
            "-c:a", "pcm_s16le",
            "-y",
            output_audio
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


def cut_and_merge_video_img(video_file, user_stamp, keep_intervals, video_id):
    output_video = f"{video_file.replace('.mp4', '')}_{user_stamp}.mp4"
    temp_file = f"temp_{video_id}.mp4"
    clip_list_file = f"clip_list_{video_id}.txt"

    try:
        cmd_copy = [
            'ffmpeg',
            '-i', video_file,
            '-c:v', 'copy',
            '-c:a', 'copy',
            temp_file
        ]
        subprocess.run(cmd_copy, check=True)

        with open(clip_list_file, 'w') as f:
            for interval in keep_intervals:
                print(f'interval={interval}')
                start, end = interval
                start_time = float_to_time_str(start)
                end_time = float_to_time_str(end)
                f.write(f"file '{temp_file}'\n")
                f.write(f"inpoint {start_time}\n")
                f.write(f"outpoint {end_time}\n")

        cmd_concat = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', clip_list_file,
            '-c:v', 'copy',
            '-c:a', 'copy',
            output_video
        ]
        subprocess.run(cmd_concat, check=True)

    except subprocess.CalledProcessError as e:
        print(f"视频处理过程中出错: {e}")
        raise
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(clip_list_file):
            os.remove(clip_list_file)

    return output_video


def time_str_to_seconds(time_str):
    time_str = time_str.replace(',', '.')
    hh_mm_ss, milliseconds = time_str.split('.')
    hh, mm, ss = hh_mm_ss.split(':')
    total_seconds = (
            int(hh) * 3600 +
            int(mm) * 60 +
            float(f"{ss}.{milliseconds}")
    )
    return round(total_seconds, 3)


def ffmpeg_cut_mp4(keep_intervals_list, video_path, video_id, user_id):
    input_video_file = video_path
    timestamp = datetime.now().strftime("%m%d_%H%M")
    keep_intervals = []
    for unit in keep_intervals_list:
        cut_start, cut_end = unit[0][0], unit[0][1]
        print(cut_start, cut_end, unit[1])
        keep_intervals.append([time_str_to_seconds(cut_start), time_str_to_seconds(cut_end)])

    input_audio = input_video_file.replace('mp4', 'wav')
    user_stamp = f'{user_id}_{timestamp}'
    output_audio = cut_and_merge_audio(input_audio, user_stamp, keep_intervals)
    output_video = cut_and_merge_video_img(input_video_file, user_stamp, keep_intervals, video_id)

    print(f'output_audio={output_audio}')
    print(f'output_video={output_video}')
    dir_name = os.path.dirname(input_video_file)
    base_name = os.path.basename(input_video_file)
    out_stamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    output_video_path = os.path.join(dir_name, f"{base_name.replace('.mp4', '')}_{user_id}_{out_stamp}.mp4")
    merge_cmd = [
        'ffmpeg', '-i', output_video, '-i', output_audio,
        '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental',
        '-y', output_video_path
    ]
    print(f'merge_cmd={merge_cmd}')
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
    print(f'cost {round(t2 - t1, 2)} s')
    return output_video_path
