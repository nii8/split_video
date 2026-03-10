import json
import sys
import time
import os
import transformers
try: import fcntl
except ImportError: fcntl = None
import settings

_data_cache = {}


def find_srt_files():
    found_files = []
    for root, dirs, files in os.walk(settings.DATA_DIR):
        for file in files:
            if '.srt' in file:
                srt_path = os.path.join(root, file)
                mp4_path, video_id, name = get_file_info(srt_path)
                if video_id in _data_cache:
                    if name != _data_cache[video_id][2]:
                        _data_cache[video_id] = [srt_path, mp4_path, name]
                    if mp4_path != _data_cache[video_id][1]:
                        _data_cache[video_id] = [srt_path, mp4_path, name]
                else:
                    _data_cache[video_id] = [srt_path, mp4_path, name]
                found_files.append([srt_path, mp4_path, name, video_id])
    return found_files


def get_file_info(file_path):
    json_path = file_path.replace('.srt', '.json')
    mp4_path = file_path.replace('.srt', '.mp4')
    if not os.path.exists(mp4_path):
        mp4_path = 0
    video_id = os.path.basename(file_path).replace('.srt', '')
    try:
        json_data = json.load(open(json_path, 'r', encoding='utf-8'))
        name = json_data.get('name', 'default')
    except:
        name = 'default'

    return mp4_path, video_id, name


def get_video_file_path(f_video_id):
    if f_video_id in _data_cache:
        return _data_cache[f_video_id][1]
    srt_list = find_srt_files()
    for srt_path, mp4_path, name, video_id in srt_list:
        if f_video_id == video_id:
            return mp4_path
    return None


def get_srt_file_path(f_video_id):
    if f_video_id in _data_cache:
        return _data_cache[f_video_id][0]
    srt_list = find_srt_files()
    for srt_path, mp4_path, name, video_id in srt_list:
        if f_video_id == video_id:
            return srt_path
    return None


def is_windows():
    """判断当前操作系统是否为Windows"""
    return sys.platform.startswith('win')


def get_token_len(prompt, tokenizer_dir="./token"):
    try:
        t1 = time.time()
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            tokenizer_dir, trust_remote_code=True
        )
        tokens = tokenizer.encode(prompt)
        token_length = len(tokens)
        t2 = time.time()
        print(f'Token length: {token_length}, cost time: {round(t2 - t1, 2)} seconds')
        return token_length

    except Exception as e:
        print(f"Error: {e}")
        return None


def parse_time_to_seconds(time_str):
    # 参数:time_str (str): 时间字符串，格式为"HH:MM:SS,mmm"
    try:
        main_part, milliseconds = time_str.split(',')
        hours, minutes, seconds = map(int, main_part.split(':'))
        milliseconds = int(milliseconds)
        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
        return total_seconds
    except ValueError:
        raise ValueError("时间格式不正确，应为'HH:MM:SS,mmm'格式")


def split_srt_content(srt_content, max_tokens=settings.LIMIT_PROMPT - 1000):
    """将SRT内容分割成多个部分，每个部分不超过max_tokens"""
    t1 = time.time()
    tokenizer = transformers.AutoTokenizer.from_pretrained("./token", trust_remote_code=True)

    paragraphs = srt_content.split('\n\n')
    parts = []
    current_part = []
    current_tokens = 0
    split_time = 0
    for para in paragraphs:
        if not para.strip():
            continue

        para_tokens = len(tokenizer.encode(para))
        if current_tokens + para_tokens > max_tokens:
            if current_part:
                print(f'para={para}')
                if '-->' in para and '\n' in para and not split_time:
                    split_time_str = para.split('-->')[0].strip().split('\n')[1]
                    split_time = parse_time_to_seconds(split_time_str)
                parts.append('\n\n'.join(current_part))
                current_part = []
                current_tokens = 0

        current_part.append(para)
        current_tokens += para_tokens

    if current_part:
        parts.append('\n\n'.join(current_part))
    t2 = time.time()
    print(f'split_srt length: {len(parts)}, cost time: {round(t2 - t1, 2)} seconds')
    return parts, split_time
