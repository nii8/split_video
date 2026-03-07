import os
import json
import re
import subprocess
import shutil
import time
from datetime import datetime

glo_input_dir = './input'
video_img_dir = '/root/xiu/data/imgs/hanbing'
glo_dic = {
    'cost': 0
}

def int_to_time(t):
    minutes = int(t // 60)
    seconds = int(t % 60)
    milliseconds = round((t - int(t)) * 30.0, 1)
    return f"{minutes}:{seconds}.{milliseconds:.1f}"


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


def get_media_duration(video_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f'{video_path} duration:', result.stdout)
        return float(result.stdout)
    except:
        return float('inf')


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
                "-c:a", "pcm_s16le",  # 保持WAV格式
                "-y",  # 覆盖已有文件
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
            "-c:a", "pcm_s16le",  # 保持WAV格式
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


def count_files_in_directory(directory_path):
    all_items = os.listdir(directory_path)
    files = [item for item in all_items if os.path.isfile(os.path.join(directory_path, item))]
    return len(files)


def cut_and_merge_img(video_file, user_stamp, keep_intervals, video_id):
    input_video_file = video_file
    output_video = f"{video_file.replace('.mp4', '')}_{user_stamp}.mp4"
    img_dir = f"{video_img_dir}/{video_id}"
    cp_img_dir = "./cp_imgs"
    os.makedirs(cp_img_dir, exist_ok=True)
    if os.path.exists(img_dir):
        pass
        # shutil.rmtree(img_dir)
    os.makedirs(img_dir, exist_ok=True)
    # ffmpeg -i $1 -vf fps=fps=30 ./imgs/frame_%06d.png

    cmd_extract = [
        "ffmpeg",
        "-i", input_video_file,
        "-vf", "fps=fps=30",
        f"{img_dir}/frame_%05d.png"
    ]
    # print(' '.join(cmd_extract))
    # subprocess.run(cmd_extract, check=True, stderr=subprocess.DEVNULL)

    frame_ranges = []
    total_t = get_media_duration(input_video_file)
    total_img_count = count_files_in_directory(img_dir)
    print(f'total_img_count={total_img_count} total_t={total_t}')
    fps = 30
    for start, end in keep_intervals:
        start_frame = round(start * fps)
        end_frame = round(end * fps)
        frame_ranges.append([start_frame, end_frame])
    all_frames = sorted([f for f in os.listdir(img_dir) if f.startswith("frame_")])
    frames_to_keep = []

    for start, end in frame_ranges:
        frames_to_keep += all_frames[start:end]

    for i, frame in enumerate(frames_to_keep):
        tar_file = f'frame_{i + 1:05d}.png'
        if i < 3:
            shutil.copy2(os.path.join(img_dir, frame), os.path.join(cp_img_dir, tar_file))
        else:
            shutil.copy2(os.path.join(img_dir, frame), os.path.join(cp_img_dir, tar_file))

    cmd_merge = [
        "ffmpeg",
        "-framerate", str(fps),
        "-i", f"{cp_img_dir}/frame_%05d.png",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-y",
        output_video
    ]
    subprocess.run(cmd_merge, check=True, stderr=subprocess.DEVNULL)
    shutil.rmtree(cp_img_dir)
    return output_video


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
        # 1. 转封装为MP4（避免重新编码）
        cmd_copy = [
            'ffmpeg',
            '-i', video_file,
            '-c:v', 'copy',
            '-c:a', 'copy',
            temp_file
        ]
        subprocess.run(cmd_copy, check=True)

        # 2. 创建剪辑列表文件
        with open(clip_list_file, 'w') as f:
            for interval in keep_intervals:
                print(f'interval={interval}')
                start, end = interval

                start_time = float_to_time_str(start)
                end_time = float_to_time_str(end)

                f.write(f"file '{temp_file}'\n")
                f.write(f"inpoint {start_time}\n")
                f.write(f"outpoint {end_time}\n")

        # 3. 无损拼接（不重新编码）
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
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(clip_list_file):
            os.remove(clip_list_file)

    return output_video






    img_dir = f"{video_img_dir}/{video_id}"
    cp_img_dir = "./cp_imgs"
    os.makedirs(cp_img_dir, exist_ok=True)
    if os.path.exists(img_dir):
        pass
        # shutil.rmtree(img_dir)
    os.makedirs(img_dir, exist_ok=True)
    # ffmpeg -i $1 -vf fps=fps=30 ./imgs/frame_%06d.png

    cmd_extract = [
        "ffmpeg",
        "-i", input_video_file,
        "-vf", "fps=fps=30",
        f"{img_dir}/frame_%05d.png"
    ]
    # print(' '.join(cmd_extract))
    # subprocess.run(cmd_extract, check=True, stderr=subprocess.DEVNULL)

    frame_ranges = []
    total_t = get_media_duration(input_video_file)
    total_img_count = count_files_in_directory(img_dir)
    print(f'total_img_count={total_img_count} total_t={total_t}')
    fps = 30
    for start, end in keep_intervals:
        start_frame = round(start * fps)
        end_frame = round(end * fps)
        frame_ranges.append([start_frame, end_frame])
    all_frames = sorted([f for f in os.listdir(img_dir) if f.startswith("frame_")])
    frames_to_keep = []

    for start, end in frame_ranges:
        frames_to_keep += all_frames[start:end]

    for i, frame in enumerate(frames_to_keep):
        tar_file = f'frame_{i + 1:05d}.png'
        if i < 3:
            shutil.copy2(os.path.join(img_dir, frame), os.path.join(cp_img_dir, tar_file))
        else:
            shutil.copy2(os.path.join(img_dir, frame), os.path.join(cp_img_dir, tar_file))

    cmd_merge = [
        "ffmpeg",
        "-framerate", str(fps),
        "-i", f"{cp_img_dir}/frame_%05d.png",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-y",
        output_video
    ]
    subprocess.run(cmd_merge, check=True, stderr=subprocess.DEVNULL)
    shutil.rmtree(cp_img_dir)
    return output_video


def get_video_fps(video_path):
    # ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 012.mp4
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    num, den = map(int, result.stdout.strip().split('/'))
    return num / den


def time_str_to_seconds(time_str):
    # 将时间字符串（格式：HH:MM:SS,SSS）转换为秒数（精确到3位小数）
    time_str = time_str.replace(',', '.')

    # 分割小时、分钟、秒+毫秒
    hh_mm_ss, milliseconds = time_str.split('.')
    hh, mm, ss = hh_mm_ss.split(':')

    # 计算总秒数
    total_seconds = (
            int(hh) * 3600 +
            int(mm) * 60 +
            float(f"{ss}.{milliseconds}")
    )

    # 四舍五入到3位小数
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
    # output_video = cut_and_merge_img(input_video_file, user_stamp, keep_intervals, video_id)
    output_video = cut_and_merge_video_img(input_video_file, user_stamp, keep_intervals, video_id)

    print(f'output_audio={output_audio}')
    print(f'output_video={output_video}')
    dir_name = os.path.dirname(input_video_file)
    base_name = os.path.basename(input_video_file)
    out_stamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    output_video_path = os.path.join(dir_name, f"{base_name.replace('.mp4', '')}_{user_id}_{out_stamp}.mp4")
    merge_cmd = f'ffmpeg -i {output_video} -i {output_audio} -c:v copy -c:a aac -strict experimental {output_video_path}'
    print(f'merge_cmd={merge_cmd}')
    os.system(merge_cmd)
    return output_video_path


def load_json_to_dict(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)  # 解析 JSON 文件
        return data
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {e}")
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
    except Exception as e:
        print(f"❌ 读取文件时发生未知错误: {e}")
    return None



def cut_video_main(keep_intervals, video_path, video_id, user_id):
    t1 = time.time()
    extract_audio(video_path)
    output_video_path = ffmpeg_cut_mp4(keep_intervals, video_path, video_id, user_id)
    t2 = time.time()
    print(f'cost {round(t2 - t1, 2)} s')
    return output_video_path





