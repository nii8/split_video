from flask import Flask, send_from_directory, request, jsonify, render_template, jsonify, send_file
import os
import uuid
import sys
import re
import datetime
import json
import time
import requests
import mylog
import config
from config import is_windows, find_srt_files, server_ip, upload_token

log = mylog.setup_logger('logs/app', 'log.txt')
app = Flask(__name__)
# 设置HLS文件的目录路径

HLS_DIR = os.path.join(os.path.dirname(__file__), 'video/hls')
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
USER_DIR = os.path.join(os.path.dirname(__file__), 'static/user')
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static/download/srt')
cfg_data = config.get_cfg_data()


@app.route("/upload_srt", methods=["POST"])
def upload_srt():
    # 1. 获取请求参数（JSON 格式或表单数据）
    data = request.get_json()
    all_text = data.get('all_text')  # 文本内容，如 'hello'
    all_name = data.get('all_name')  # 文件名，如 'test.txt'
    ch_text = data.get('ch_text')
    ch_name = data.get('ch_name')
    eng_text = data.get('eng_text')
    eng_name = data.get('eng_name')
    all_name = all_name.replace("'", '').replace('"', '').replace(' ', '')

    if not all_text or not all_name:
        return jsonify({"error": "Missing 'content' or 'all_name'"}), 400

    # 2. 将文本写入文件
    file_path = os.path.join(UPLOAD_DIR, all_name)
    try:
        log.info(f'file_path={file_path}')
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(all_text)
    except Exception as e:
        print(f'err={str(e)}')
        return jsonify({"error": f"Failed to write file {all_name}: {str(e)}"}), 500

    file_path = os.path.join(UPLOAD_DIR, ch_name)
    try:
        print(f'file_path={file_path}')
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(ch_text)
    except Exception as e:
        return jsonify({"error": f"Failed to write file {ch_name}: {str(e)}"}), 500

    file_path = os.path.join(UPLOAD_DIR, eng_name)
    try:
        print(f'file_path={file_path}')
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(eng_text)
    except Exception as e:
        return jsonify({"error": f"Failed to write file {eng_name}: {str(e)}"}), 500

    # 3. 返回下载 URL（假设服务运行在 http://localhost:5000）
    all_url = f"http://kaixin.wiki/download/{all_name}"
    ch_url = f"http://kaixin.wiki/download/{ch_name}"
    eng_url = f"http://kaixin.wiki/download/{eng_name}"
    print(f'all_url={all_url}')
    print(f'all_url={ch_url}')
    print(f'all_url={eng_url}')
    return jsonify({
        "message": "File created successfully",
        "all_url": all_url,
        "ch_url": ch_url,
        "eng_url": eng_url
    })


@app.route("/download/<file_name>", methods=["GET"])
def download_file(file_name):
    # 检查文件是否存在
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # 返回文件下载（自动处理 MIME 类型）
    return send_file(
        file_path,
        as_attachment=True,
        download_name=file_name
    )


# 更新播放进度 update_play_progress delete

# 用户播放计数 increment_play_count delete


@app.route('/get_play_list', methods=['POST'])
def get_play_list():
    data = request.get_json()
    video_set = data.get('video_set')
    openid = data.get('openid')
    play_list = []
    list_file = os.path.join(os.path.dirname(__file__), f'video/src/{video_set}/list.txt')

    if os.path.exists(list_file):
        with open(list_file, 'r') as f:
            for line in f:
                if line.strip() and '-' in line:
                    id_str, name, item_type = line.strip().split('-', 2)
                    title_id = name.split('.')[0]
                    # play_count, play_percent, video_day = get_user_video_data(openid, video_set, id_str, title_id)
                    play_count, play_percent, video_day = 1, 1, 1
                    play_list.append({
                        'id_str': id_str,
                        'name': name,
                        'item_type': item_type,
                        'play_count': play_count,
                        'video_day': video_day,
                        'play_percent': play_percent  # 上次播放的进度百分比
                    })

    return jsonify(play_list)


# 提交弹幕 保留
@app.route('/submit_content', methods=['POST'])
def submit_content():
    data = request.get_json()
    openid = data.get('openid')
    content_type = data.get('type')  # danmu/label/dry/gold_txt
    content = data.get('content')
    video_set = data.get('video_set')
    id_str = data.get('id_str')
    current_time = data.get('current_time')
    timestamp_str = data.get('timestamp_str')
    real_timestamp = data.get('real_timestamp')

    if not openid:
        return jsonify({'success': 0, 'error': 'invalid openid'})

    user_id = 1
    nick_name = 1
    avatar_url = 1

    # 统一存储到视频目录
    content_dir = f'/root/xiu/data/{video_set}/{id_str}'
    os.makedirs(content_dir, exist_ok=True)

    target_file = f'{content_dir}/{content_type}.json'

    content_data = {
        'user_id': user_id,
        'nick_name': nick_name,
        'avatar_url': avatar_url,
        'video_set': video_set,
        'id_str': id_str,
        'content': content,
        'video_time': current_time,
        'timestamp': real_timestamp,
        'timestamp_str': timestamp_str
    }

    # 读取现有数据或初始化
    existing_data = []
    if os.path.exists(target_file):
        with open(target_file, 'r') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []

    existing_data.append(content_data)

    with open(target_file, 'w') as f:
        json.dump(existing_data, f, indent=4, ensure_ascii=False)

    return jsonify({
        'success': 1,
        'message': 'Content submitted successfully'
    })


def ensure_user_data_dir(user_id):
    """确保用户数据目录存在"""
    user_dir = f'/root/xiu/data/user/{user_id}'
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


# 获取弹幕  保留
@app.route('/get_content', methods=['POST'])
def get_content():
    data = request.get_json()
    video_set = data.get('video_set')
    id_str = data.get('id_str')
    openid = data.get('openid')

    result = {
        'danmu': [],
        'label': [],
        'gold_txt': [],
        'dry': []
    }
    # 统一从视频目录获取所有类型数据
    content_dir = f'/root/xiu/data/{video_set}/{id_str}'
    for content_type in ['danmu', 'label', 'gold_txt', 'dry']:
        content_file = f'{content_dir}/{content_type}.json'
        if os.path.exists(content_file):
            with open(content_file, 'r') as f:
                try:
                    result[content_type] = json.load(f)
                except json.JSONDecodeError:
                    result[content_type] = []

    return jsonify({
        'success': 1,
        'data': result
    })


@app.route('/hls/<path:filename>')
def hls_files(filename):
    return send_from_directory(HLS_DIR, filename)


# 记录播放行为 report_play_event delete
# 获取用户上次播放时间戳 get_last_play_timestamp delete
def get_user_id(token):
    token_list = cfg_data['token_list']
    if token in token_list:
        user_index = token_list.index(token)
        user_id = '%03d'%(user_index+1)
        return user_id
    return None


def get_video_list():
    video_id_list = []
    srt_list = find_srt_files()
    for srt_path, mp4_path, name, video_id in srt_list:
        video_id_list.append([video_id, name])
    return video_id_list


@app.route('/api/get_video_id_list', methods=['POST'])
def get_video_id_list():
    # 获取前端发送的数据
    data = request.get_json()
    token = data.get('token')
    token_list = cfg_data['token_list']
    if token not in token_list:
        return jsonify({'error': 'Missing token'}), 400
    video_id_list = get_video_list()
    return jsonify({
        'status': 'success',
        'video_id_list': video_id_list
    })


@app.route('/upload_video_srt', methods=['POST'])
def upload_video_srt():
    data = request.get_json()
    if not data or data.get('token') != upload_token:
        return jsonify({"error": "Invalid token"}), 401

    srt_path = data.get('srt_path')
    srt_content = data.get('srt_content')

    if not srt_path or not srt_content:
        return jsonify({"error": "Missing params"}), 400

    try:
        os.makedirs(os.path.dirname(srt_path), exist_ok=True)
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/get_backend_url', methods=['POST'])
def get_backend_url():
    # 获取前端发送的数据
    data = request.get_json()
    video_id = data.get('video_id')
    prompt = data.get('prompt')
    token = data.get('token')
    user_id = get_user_id(token)
    token_list = cfg_data['token_list']
    name_dic = cfg_data['name_dic']

    # 验证必要参数
    if not video_id or not prompt:
        return jsonify({'error': 'Missing video_id or prompt'}), 400
    if token not in token_list:
        return jsonify({'error': 'Missing token'}), 400
    '''
    'busy1_sse_chat'                         # 5min
    'done1_sse_chat__1|2|3'                  # 3min
    'busy2_sse_chat_v2'                      # 5min
    'done2_sse_chat_v2__1|2|3'               # 3min
    'busy3_generate_time_sequence'           # 3min
    'done3_generate_time_sequence__1|2|3'    # 3min
    'busy4_generate_video'                   # 15min
    'done4_generate_video__1|2|3|4'          # 3min
    
    '''
    name = ''
    url_cfg = config.get_json_data()
    # socket_status.json
    for key_num, value in url_cfg.items():
        if user_id == value.get('user_id') and 'done' in value.get('status'):
            name = name_dic[key_num]
            break
    if not name:
        for key_num, value in url_cfg.items():
            if user_id == value.get('user_id') and 'free' == value.get('status'):
                name = name_dic[key_num]
                break
    if not name:
        for key_num, value in url_cfg.items():
            if 'free' == value.get('status'):
                name = name_dic[key_num]
                break
    name_list = []
    if not name:
        for key_num, value in url_cfg.items():
            if 'done' in value.get('status') and int(time.time() - value.get('cur_time')) > 180:
                name = name_dic[key_num]
                name_list.append([int(time.time() - value.get('cur_time')), name])
    if name_list:
        max_element = max(name_list, key=lambda x: x[0])
        name = max_element[1]

    status = 'busy'
    backend_url = 'http://localhost:5001/'
    if name:
        status = 'free'
        port_id = int(name.split('backend')[1])
        if is_windows():
            backend_url = f"http://localhost:{5000 + port_id}/{name}" if status == 'free' else ''
        else:
            backend_url = f"http://{server_ip}:{5000 + port_id}/{name}" if status == 'free' else ''



    # 返回结果
    return jsonify({
        'status': 'success',
        'backend_url': backend_url,
        'video_id': video_id,
        'user_id': user_id,
        'backend_status': status
    })


@app.route('/video_text.html')
def video_text():
    video_set = 'hanbing'
    title = '短视频文案生成器'
    return render_template('video_text.html', video_set=video_set, title=title)


@app.route('/video.html')
def video():
    video_set = 'hanbing'
    id_str = request.args.get('id_str', '001')
    openid = request.args.get('openid')
    title = '智能文案剪辑'
    return render_template('video.html', video_set=video_set, id_str=id_str, title=title)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dizi/01.html')
def dizi01():
    return render_template('dizi/01.html')


@app.route('/health_check')
def health_check():
    return {'status': 'healthy'}, 200

def get_hls_id(hls_dir):
    count = 0
    for filename in os.listdir(hls_dir):
        count += 1
    count += 1
    return '%03d' % count


def split_video():
    src_dir = "video/src"
    hls_dir = "video/hls"
    entries = os.listdir(src_dir)
    folders = [entry for entry in entries if os.path.isdir(os.path.join(src_dir, entry))]
    print("视频列表:", folders)  # kaixin zhexue zhihui
    for folder in folders:
        child_dir = os.path.join(src_dir, folder)
        mp4_files = []
        for filename in os.listdir(child_dir):
            if filename.endswith('.mp4'):
                mp4_files.append(filename)
        mp4_files.sort()
        for filename in mp4_files:
            file_id = filename.split('-')[0]
            g_child_dir = os.path.join(src_dir, folder, file_id)  # video/src/zhexue/1
            if not os.path.exists(g_child_dir):
                os.makedirs(g_child_dir, exist_ok=True)
                input_video = os.path.join(child_dir, filename)
                run_cmd = f'sh fff.sh {input_video} {g_child_dir}'
                log.info(f'run_cmd: {run_cmd}')
                os.system(run_cmd)
                m3u8_list = []
                for ts_name in os.listdir(g_child_dir):
                    if '.m3u8' in ts_name:
                        ts_id = ts_name.replace('.m3u8', '').replace('part', '')
                        m3u8_list.append([ts_name, ts_id])
                m3u8_list.sort(key=lambda x: int(x[1]))
                hls_child_dir = os.path.join(hls_dir, folder)
                hls_id_list = []
                for ts_name, ts_id in m3u8_list:
                    hls_id = get_hls_id(hls_child_dir)
                    hls_id_list.append([hls_id, ts_id])
                    ts_dir = os.path.join(hls_child_dir, hls_id)
                    os.makedirs(ts_dir, exist_ok=True)  # video/src/zhexue/001
                    with open(os.path.join(g_child_dir, ts_name), 'r') as f:
                        for line in f:
                            if line.startswith('part'):
                                mv_cmd = f'mv {g_child_dir}/{line.strip()} {ts_dir}/.'
                                os.system(mv_cmd)
                        mv_cmd = f'mv {g_child_dir}/{ts_name} {ts_dir}/output.m3u8'
                        os.system(mv_cmd)
                list_txt_path = os.path.join(child_dir, 'list.txt')
                list_txt_lines = ''
                with open(list_txt_path, 'r') as f:
                    list_txt_lines = f.readlines()
                for i, line in enumerate(list_txt_lines):
                    if len(line.split('-')) == 2:  # 例子: 我为什么要讲生死-video
                        list_append_list = []
                        for hls_id, ts_id in hls_id_list:
                            title = line.split('-')[0]
                            media = line.split('-')[1]
                            list_append_str = f'{hls_id}-{file_id}.{ts_id}.{title}-{media}'
                            list_append_list.append(list_append_str)
                        list_txt_lines = list_txt_lines[:i] + list_append_list + list_txt_lines[i + 1:]
                        break
                with open(list_txt_path, 'w') as f:
                    for line in list_txt_lines:
                        f.write(line)

                debug = 1



if __name__ == '__main__':

    if is_windows():
        app.run(host='0.0.0.0', port=5000)
    else:
        app.run(host='0.0.0.0', port=80, debug=False)

