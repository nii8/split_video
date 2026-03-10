import json
import time
import os
import requests
import shutil
try: import fcntl
except ImportError: fcntl = None
from datetime import datetime
from make_video.step3 import cut_video_main
import settings
from config import is_windows, get_token_len, split_srt_content, find_srt_files, get_video_file_path

data_unit_name = 'hanbing'
img_dir = './data/imgs/hanbing'
debug_mode = False

def send_srt(srt_path, srt_content):
    try:
        response = requests.post(f"http://{settings.SERVER_IP}:80/upload_video_srt",
            json={
                "srt_path": srt_path,
                "srt_content": srt_content,
                "token": settings.UPLOAD_TOKEN
            }, timeout=6
        )
        print('send 200')
        return response.status_code == 200
    except Exception as e:
        print(f'send fail - 未知错误: {str(e)}')
        return False

def get_video_imgs(video_id, mp4_path, srt_path):
    video_img_dir = os.path.join(img_dir, video_id)
    if os.path.exists(video_img_dir):
        shutil.rmtree(video_img_dir)
    os.makedirs(video_img_dir, exist_ok=True)
    srt_content = None
    with open(srt_path, 'r', encoding='utf-8') as f:
        srt_content = f.read()
        if debug_mode:
            send_srt(srt_path, srt_content)
        full_tokens = get_token_len(srt_content)
        if full_tokens is not None and full_tokens + 300 <= settings.LIMIT_PROMPT:
            get_img_cmd = f'ffmpeg -i {mp4_path} -vf fps=fps=30 {video_img_dir}/frame_%06d.png'
        else:
            srt_parts, split_time = split_srt_content(srt_content)
            split_count = int(split_time * 30)
            get_img_cmd = f'ffmpeg -i {mp4_path} -frames:v {split_count} -vf fps=fps=30 {video_img_dir}/frame_%06d.png'

    print(f'get_img_cmd={get_img_cmd}')
    t1 = time.time()
    if srt_content:
        send_srt(srt_path, srt_content)
    t2 = time.time()
    print('get_img time:', round(t2-t1,1), 's')


def get_first_pending_task(file_path='user_task.json'):
    """读取JSON文件，返回第一个status为pending的任务的keep_intervals"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if not is_windows():
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f'get_first_pending_task JSONDecodeError')
                data = []

            if not is_windows():
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        for task in data:
            if task.get('status') == 'pending':
                return task

        return None
    except Exception:
        return None


def get_new_video(file_path='video_list.json'):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            videos = json.load(f)
        except json.JSONDecodeError:
            print(f'get_new_video JSONDecodeError')
            videos = []

        updated = False

        srt_list = find_srt_files()
        for srt_path, mp4_path, name, video_id in srt_list:
            if video_id not in videos:
                print(f'srt_list2 = {srt_list}')
                get_video_imgs(video_id, mp4_path, srt_path)
                videos.append(video_id)
                updated = True
                break

        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(videos, f, ensure_ascii=False, indent=2)
        return updated


def update_task_status(user_id, video_id, new_status, oss_path=None, file_path='user_task.json'):
    """根据user_id和video_id更新任务的status状态"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if not is_windows():
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                except OSError as e:
                    raise RuntimeError(f"获取文件锁失败: {e}")

            try:
                tasks = json.load(f)
            except json.JSONDecodeError:
                print(f'update_task_status JSONDecodeError')
                tasks = []

            updated = False

            for task in tasks:
                if task.get('user_id') == user_id and task.get('video_id') == video_id:
                    task['status'] = new_status
                    if oss_path:
                        task['oss_path'] = oss_path
                    updated = True
                    break

            # 原子写入：先写临时文件，再替换，防止崩溃导致 JSON 损坏
            if updated:
                tmp_path = file_path + '.tmp'
                with open(tmp_path, 'w', encoding='utf-8') as tmp:
                    json.dump(tasks, tmp, ensure_ascii=False, indent=2)
                os.replace(tmp_path, file_path)
            if not is_windows():
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return updated

    except Exception as e:
        print(f"更新状态失败: {e}")
        return False


def find_mp4_files(video_path):
    dir_path = os.path.dirname(os.path.abspath(video_path))
    mp4_files = []
    for file in os.listdir(dir_path):
        if file.lower().endswith('.mp4'):
            mp4_files.append(os.path.join(dir_path, file))
    return mp4_files


def strftime_to_timestamp(formatted_time):
    try:
        dt = datetime.strptime(formatted_time, "%Y_%m_%d_%H_%M_%S")
        return int(dt.timestamp())
    except ValueError:
        return None


def upload_video(video_path, video_id, user_id):
    mp4_files = find_mp4_files(video_path)
    dir_name = os.path.dirname(video_path)
    print(f'dir_name={dir_name}')
    file_list = []
    for mp4_file in mp4_files:
        base_name = os.path.basename(mp4_file)
        if f'{video_id}_{user_id}_' in base_name:
            timestamp = strftime_to_timestamp(base_name.replace('.mp4', '').replace(f'{video_id}_{user_id}_', ''))
            if timestamp:
                file_list.append([timestamp, mp4_file, base_name])
    file_list.sort(reverse=True, key=lambda x: x[0])

    if file_list:
        latest_timestamp, latest_mp4_file, mp4_file_name = file_list[0]
        oss_dir = latest_mp4_file.replace(mp4_file_name, '').split(data_unit_name)[1]
        cmd = f'ossutil cp {latest_mp4_file} oss://kaixin1109/{data_unit_name}{oss_dir}{mp4_file_name}'
        oss_path = f'http://video.kaixin.wiki/{data_unit_name}{oss_dir}{mp4_file_name}'
        print(f'cmd={cmd}')
        print(f'oss_path={oss_path}')
        os.system(cmd)
        return oss_path
    else:
        print("未找到要上传的视频文件")
        return None


if __name__ == '__main__':
    while True:
        get_new_video()
        task = get_first_pending_task()
        if task:
            keep_intervals = task.get('keep_intervals')
            user_id = task.get('user_id')
            video_id = task.get('video_id')
            print(user_id, video_id)
            video_path = get_video_file_path(video_id)
            if keep_intervals and user_id and video_id and video_path:
                print(user_id, video_path)
                update_task_status(user_id, video_id, "processing")
                cut_video_main(keep_intervals, video_path, video_id, user_id)
                update_task_status(user_id, video_id, "uploading")
                oss_path = upload_video(video_path, video_id, user_id)
                update_task_status(user_id, video_id, "completed", oss_path)
        time.sleep(10)
