import json
import os
try: import fcntl
except ImportError: fcntl = None
from datetime import datetime
from flask import Flask, request, jsonify
import settings
from config import is_windows, get_video_file_path


app = Flask(__name__)

# JSON文件路径
USER_TASK_FILE = 'user_task.json'
debug_mode = False


def load_tasks():
    """从JSON文件加载所有任务"""
    if not os.path.exists(USER_TASK_FILE):
        return []

    try:
        with open(USER_TASK_FILE, 'r', encoding='utf-8') as f:
            if not is_windows():
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # 共享读锁
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f'load_tasks JSONDecodeError')
                data = []
            if not is_windows():
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_tasks(tasks):
    """保存任务到JSON文件"""
    try:
        with open(USER_TASK_FILE, 'w', encoding='utf-8') as f:
            if not is_windows():
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(tasks, f, ensure_ascii=False, indent=2)
            if not is_windows():
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return True
    except Exception as e:
        print(f"保存文件时出错: {e}")
        return False


def validate_keep_intervals(keep_intervals):
    """验证keep_intervals参数格式"""
    if not isinstance(keep_intervals, list):
        return False

    for interval in keep_intervals:
        if not isinstance(interval, list) or len(interval) != 2:
            return False
    return True


@app.route('/make_video', methods=['POST'])
def make_video():
    """
    处理创建视频任务的POST请求
    接收参数：
    - video_id: 视频ID
    - user_id: 用户ID
    - keep_intervals: 保留的时间区间列表，格式如 [[start1, end1], [start2, end2]]
    """
    try:
        # 获取JSON格式的请求数据
        data = request.get_json()

        # 检查必需参数
        required_fields = ['video_id', 'user_id', 'keep_intervals']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'message': f'缺少必要参数: {field}'
                }), 400

        # 提取参数
        video_id = str(data['video_id'])
        user_id = str(data['user_id'])
        keep_intervals = data['keep_intervals']

        # 验证参数
        if not video_id or not user_id:
            return jsonify({
                'code': 400,
                'message': 'video_id和user_id不能为空'
            }), 400

        if not validate_keep_intervals(keep_intervals):
            return jsonify({
                'code': 400,
                'message': 'keep_intervals格式错误，应为[[start1, end1], [start2, end2]]格式，且start<end'
            }), 400

        if video_id:
            mp4_path = get_video_file_path(video_id)
            if not mp4_path:
                return jsonify({
                    'code': 200,
                    'message': '没有视频文件',
                    'data': {
                        'task_id': 0,
                        'video_id': 0,
                        'user_id': 0,
                        'keep_intervals': 0
                    }
                })
        # 创建任务对象
        task = {
            'video_id': video_id,
            'user_id': user_id,
            'keep_intervals': keep_intervals,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'pending'  # 任务状态：pending, processing, completed, failed
        }

        # 加载现有任务
        tasks = load_tasks()

        # 检查是否已存在相同video_id和user_id的任务
        existing_task = next(
            (t for t in tasks if t['video_id'] == video_id and t['user_id'] == user_id),
            None
        )

        if existing_task:
            # 更新现有任务
            if not debug_mode:
                existing_task.update(task)
            message = '任务已更新'
        else:
            # 添加新任务
            tasks.append(task)
            message = '任务已添加'

        # 保存到文件
        if save_tasks(tasks):
            return jsonify({
                'code': 200,
                'message': message,
                'data': {
                    'task_id': f"{user_id}_{video_id}",
                    'video_id': video_id,
                    'user_id': user_id,
                    'keep_intervals': keep_intervals
                }
            })
        else:
            return jsonify({
                'code': 500,
                'message': '保存任务失败，请稍后重试'
            }), 500

    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'服务器内部错误: {str(e)}'
        }), 500


@app.route('/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务列表"""
    try:
        tasks = load_tasks()

        # 可选：根据查询参数过滤任务
        user_id = request.args.get('user_id')
        video_id = request.args.get('video_id')

        if user_id:
            tasks = [t for t in tasks if t['user_id'] == user_id]

        if video_id:
            tasks = [t for t in tasks if t['video_id'] == video_id]

        return jsonify({
            'code': 200,
            'data': {
                'tasks': tasks,
                'total': len(tasks)
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取任务列表失败: {str(e)}'
        }), 500


@app.route('/get_task', methods=['POST'])
def get_task():
    """获取特定任务（POST 版本）"""
    try:
        # 从 JSON 请求体获取 user_id 和 video_id
        data = request.get_json()
        if not data or 'user_id' not in data or 'video_id' not in data:
            return jsonify({
                'code': 400,
                'message': '缺少 user_id 或 video_id 参数'
            }), 400

        user_id = data['user_id']
        video_id = data['video_id']

        # 模拟加载任务数据
        tasks = load_tasks()  # 假设 load_tasks() 已定义
        print(user_id, video_id)

        # 查找匹配的任务
        task = next(
            (t for t in tasks if t['user_id'] == user_id and t['video_id'] == video_id),
            None
        )

        if task:
            if 'keep_intervals' in task:
                del task['keep_intervals']
            return jsonify({
                'code': 200,
                'data': task
            })
        else:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404

    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取任务失败: {str(e)}'
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'code': 200,
        'message': '服务运行正常',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    # 确保JSON文件存在
    if not os.path.exists(USER_TASK_FILE):
        with open(USER_TASK_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

    # 启动Flask应用
    app.run(host='0.0.0.0', port=8868, debug=True)