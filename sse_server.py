import mylog
import sys
import os
import json
import time
try: import fcntl
except ImportError: fcntl = None
import transformers
import requests
from openai import OpenAI
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from datetime import datetime
from config import Config, is_windows, get_token_len, limit_prompt, split_srt_content, get_srt_file_path
from make_time.step2 import get_keep_intervals

data_dic = {}
servers = ["113.249.107.180", "113.249.107.182"]
port = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
backend_name = sys.argv[2] if len(sys.argv) > 2 else 'backend1'
backend_id = sys.argv[3] if len(sys.argv) > 3 else 'c0929290-6d79-40de-af54-e8aae8072060'
backend_key = sys.argv[4] if len(sys.argv) > 4 else '001'
log = mylog.setup_logger(f'logs/{backend_name}', f'{backend_name}.txt')
app = Flask(__name__)
CORS(app)

client = OpenAI(
    api_key=Config.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


def update_socket_status(backend_key, status_str, user_id):
    """
    更新socket状态

    参数:
    - backend_key: socket编号，如 '001'
    - status_str: 状态字符串，如 'busy1', 'free'等
    - file_path: JSON文件路径

    返回值:
    - bool: 更新成功返回True，失败返回False
    """
    file_path = './data/config/socket_status.json'
    try:
        # 读取并更新JSON文件
        with open(file_path, 'r+', encoding='utf-8') as f:
            # 获取文件锁（仅限非Windows系统）
            if not is_windows():
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                except OSError as e:
                    print(f"获取文件锁失败: {e}")
                    return False


            # 加载JSON数据
            try:
                status_dict = json.load(f)
            except json.JSONDecodeError:
                print(f'update_socket_status JSONDecodeError')
                status_dict = {}

            # 检查backend_key是否存在
            if backend_key not in status_dict:
                print(f"错误: backend_key '{backend_key}' 不存在于文件中")
                if not is_windows():
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return False

            # 更新状态和时间
            status_dict[backend_key]['status'] = status_str
            status_dict[backend_key]['cur_time'] = time.time()
            status_dict[backend_key]['user_id'] = user_id

            # 可选：添加格式化的时间字符串，便于阅读
            status_dict[backend_key]['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 将文件指针移到开头，清空文件，写入新数据
            f.seek(0)
            f.truncate()
            json.dump(status_dict, f, ensure_ascii=False, indent=2)
            if not is_windows():
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return True

    except FileNotFoundError:
        print(f"错误: 文件 {file_path} 不存在")
        return False
    except PermissionError:
        print(f"错误: 没有权限访问文件 {file_path}")
        return False
    except Exception as e:
        print(f"更新socket状态失败: {e}")
        return False


def get_srt_prompt(prompt, video_id):
    """获取SRT内容并分割成多个prompt部分"""

    file_path = get_srt_file_path(video_id)

    
    if not file_path:
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        srt_content = f.read()
    
    # 检查是否需要分割
    full_prompt = prompt + '\n\n' + srt_content
    full_tokens = get_token_len(full_prompt)
    
    if full_tokens is not None and full_tokens <= limit_prompt:
        return [full_prompt]
    
    # 需要分割SRT内容
    srt_parts, split_time = split_srt_content(srt_content)
    prompt_parts = []
    for part in srt_parts:
        prompt_parts.append(prompt + '\n\n' + part)
    
    return prompt_parts


def llm_generate_stream(prompt):
    """使用 DeepSeek API 流式生成文本"""
    if not prompt:
        log.error("解析字幕文件出错")
        yield "解析字幕文件出错"
        return

    log.info(f"收到请求，准备生成文案")

    try:
        # 调用 DeepSeek API 并启用流式传输
        response = client.chat.completions.create(
            model='deepseek-chat',  # DeepSeek 模型名称
            messages=[
                {"role": "system", "content": "You are a senior short video copywriter well-versed in the dissemination patterns of the TikTok platform."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=limit_prompt,
            stream=True  # 关键：启用流式输出
        )

        # 处理流式响应
        for chunk in response:
            if hasattr(chunk.choices[0], "delta") and chunk.choices[0].delta.content:
                word = chunk.choices[0].delta.content
                # time.sleep(1)
                yield word

    except Exception as e:
        log.error(f"API 调用失败: {str(e)}")
        yield f"生成文案时出错: {str(e)}"


@app.route('/health_check', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy'
    })


@app.route(f'/{backend_id}-{backend_name}/sse-chat', methods=['GET'])
def sse_chat():
    """SSE流式聊天接口"""
    prompt = request.args.get('prompt', '')
    user_id = request.args.get('user_id', 'unknown')
    video_id = request.args.get('video_id', '')
    
    log.info(f"用户 {user_id} 发送消息: {prompt[:10]}")
    update_socket_status(backend_key, 'busy1_sse_chat', user_id)  # 5min
    # 获取分割后的prompt列表
    prompt_parts = get_srt_prompt(prompt, video_id)
    
    def event_stream():
        try:
            if not prompt_parts:
                error_event = {
                    'error': '服务端缺少字幕srt文件',
                    'timestamp': time.time()
                }
                yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                raise Exception("出错了, 服务端缺少字幕srt文件")
            # 发送开始事件
            start_event = {
                'status': 'started',
                'timestamp': time.time(),
                'user_id': user_id,
                'total_parts': len(prompt_parts)
            }
            yield f"event: start\ndata: {json.dumps(start_event, ensure_ascii=False)}\n\n"
            full_response = ""
            # 处理每个prompt部分
            for part_idx, part_prompt in enumerate(prompt_parts):
                log.info(f"处理第 {part_idx + 1}/{len(prompt_parts)} 部分: {get_token_len(part_prompt)}token")
                # 流式生成响应
                for i, chunk in enumerate(llm_generate_stream(part_prompt)):
                    full_response += chunk
                    event_data = {
                        'text': chunk,
                        'index': i,
                        'type': 'chunk',
                        'part_index': part_idx,
                        'full_response': full_response,
                        'timestamp': time.time()
                    }
                    yield f"event: message\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                break

            # 发送结束事件
            end_event = {
                'status': 'completed',
                'timestamp': time.time()
            }
            yield f"event: end\ndata: {json.dumps(end_event, ensure_ascii=False)}\n\n"
            update_socket_status(backend_key, 'done1_sse_chat__1', user_id)  # 3min
            log.info(f"用户 {user_id} 请求完成")

        except Exception as e:
            log.error(f"处理请求时出错: {str(e)}")
            error_event = {
                'error': str(e),
                'timestamp': time.time()
            }
            yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"
            update_socket_status(backend_key, 'done1_sse_chat__2', user_id)  # 3min
        finally:
            update_socket_status(backend_key, 'done1_sse_chat__3', user_id)  # 3min
            log.info(f"客户端断开连接")

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'X-Accel-Buffering': 'no'  # 禁用Nginx缓冲
        }
    )


@app.route(f'/{backend_id}-{backend_name}/sse-chat', methods=['OPTIONS'])
def sse_chat_options():
    """处理预检请求"""
    return '', 200, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }


@app.route(f'/{backend_id}-{backend_name}/sse-chat-v2', methods=['GET'])
def sse_chat_v2():
    """SSE流式聊天接口 - 第二阶段脚本生成"""
    prompt = request.args.get('prompt', '')
    user_id = request.args.get('user_id', 'unknown')
    video_id = request.args.get('video_id', '')
    update_socket_status(backend_key, 'busy2_sse_chat_v2', user_id)  # 5min
    log.info(f"用户 {user_id} 发送第二阶段请求，视频ID: {video_id}")
    def event_stream():
        try:
            # 发送开始事件
            start_event = {
                'status': 'started',
                'timestamp': time.time(),
                'user_id': user_id,
                'stage': 'script_generation'
            }
            yield f"event: start\ndata: {json.dumps(start_event, ensure_ascii=False)}\n\n"

            # 流式生成响应
            full_response = ""
            for i, chunk in enumerate(llm_generate_stream(prompt)):
                full_response += chunk
                event_data = {
                    'text': chunk,
                    'index': i,
                    'type': '',
                    'full_response': full_response,
                    'timestamp': time.time()
                }
                yield f"event: message\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"

            # 发送结束事件
            end_event = {
                'status': 'completed',
                'full_response': full_response,
                'timestamp': time.time()
            }
            yield f"event: end\ndata: {json.dumps(end_event, ensure_ascii=False)}\n\n"
            update_socket_status(backend_key, 'done2_sse_chat_v2__1', user_id)  # 3min
            log.info(f"用户 {user_id} 第二阶段请求完成，总响应长度: {len(full_response)}")

        except Exception as e:
            log.error(f"处理第二阶段请求时出错: {str(e)}")
            error_event = {
                'error': str(e),
                'timestamp': time.time()
            }
            yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"
            update_socket_status(backend_key, 'done2_sse_chat_v2__2', user_id)  # 3min
        finally:
            log.info(f"客户端 {user_id} 断开第二阶段连接")
            update_socket_status(backend_key, 'done2_sse_chat_v2__3', user_id)  # 3min

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'X-Accel-Buffering': 'no'  # 禁用Nginx缓冲
        }
    )


@app.route(f'/{backend_id}-{backend_name}/sse-chat-v2', methods=['OPTIONS'])
def sse_chat_v2_options():
    """处理第二阶段预检请求"""
    return '', 200, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }


def execute_on_server(run_ip, make_video_data):
    """在指定执行机上执行视频生成"""
    try:
        response = requests.post(
            f'http://{run_ip}:8868/make_video',
            json=make_video_data,
            timeout=600
        )

        if response.status_code == 200:
            result = response.json()
            return True, result
        return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)


@app.route(f'/{backend_id}-{backend_name}/sse-generate-video', methods=['GET'])
def sse_generate_video():
    """SSE视频生成接口 - 第四阶段"""
    data = json.loads(request.args.get('data', '{}'))
    video_id = data.get('video_id', '')
    user_id = data.get('user_id', '001')
    keep_intervals = data.get('keep_intervals', [])
    stage = data.get('stage', 4)
    log.info(f"用户 {user_id} 发送视频生成请求，视频ID: {video_id}, 时间序列数: {len(keep_intervals)}")
    update_socket_status(backend_key, 'busy4_generate_video', user_id)  # 15min
    def event_stream():
        try:
            # 发送开始事件
            start_event = {
                'status': 'started',
                'timestamp': time.time(),
                'user_id': user_id,
                'video_id': video_id,
                'stage': stage,
                'message': '视频生成任务已开始'
            }
            yield f"event: start\ndata: {json.dumps(start_event, ensure_ascii=False)}\n\n"

            # 第一次请求：启动视频生成
            log.info(f"开始第一次请求：启动视频生成")

            # 准备请求数据（根据实际API需求调整）
            make_video_data = {
                'video_id': video_id,
                'user_id': user_id,
                'keep_intervals': keep_intervals
            }

            # 第一次请求 - 启动视频生成
            real_ip = None

            # 遍历执行机
            for run_ip in servers:
                log.info(f"尝试在服务器 {run_ip} 上执行")

                success, result = execute_on_server(run_ip, make_video_data)

                if success and isinstance(result, dict) and result.get('data', {}).get('task_id', 0) != 0:
                    real_ip = run_ip
                    log.info(f"服务器 {run_ip} 视频生成启动成功: {result}")

                    progress_event = {
                        'progress': 1,
                        'message': '视频生成任务已启动',
                        'timestamp': time.time()
                    }
                    yield f"event: message\ndata: {json.dumps(progress_event, ensure_ascii=False)}\n\n"
                    break  # 成功则退出循环
                else:
                    log.warning(f"服务器 {run_ip} 执行失败或没有数据: {result}")

            # 如果所有服务器都失败了
            if real_ip is None:
                error_event = {
                    'progress': 0,
                    'message': '所有执行机没有视频数据',
                    'timestamp': time.time()
                }
                yield f"event: message\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                raise Exception("所有执行机都失败或没有数据")


            # 后续99次请求：轮询进度并获取视频URL
            video_url = None
            max_retries = 9999999
            retry_i = 0
            retry_break = 99
            retry_interval = 30  # 30秒间隔

            for i in range(max_retries):
                try:
                    log.info(f"第{i + 2}次请求：查询视频生成进度")

                    # 构建查询请求数据
                    get_video_data = {
                        'video_id': video_id,
                        'user_id': user_id
                    }

                    # 查询视频生成状态
                    response = requests.post(
                        f'http://{real_ip}:8868/get_task',
                        json=get_video_data,
                        timeout=60
                    )

                    if response.status_code == 200:
                        result = response.json()
                        log.info(f"进度查询结果: {result}")

                        # 计算进度百分比
                        progress_percent = retry_i
                        res_data = result.get('data', {})
                        # 检查是否生成完成并包含视频URL
                        if res_data.get('status') == 'completed' and res_data.get('oss_path'):
                            video_url = res_data.get('oss_path')
                            log.info(f"视频生成完成，URL: {video_url}")

                            # 发送视频URL事件
                            video_url_event = {
                                'video_url': video_url,
                                'message': '视频生成完成',
                                'timestamp': time.time()
                            }
                            yield f"event: video_url\ndata: {json.dumps(video_url_event, ensure_ascii=False)}\n\n"

                            # 发送最终进度消息
                            progress_event = {
                                'progress': 100,
                                'message': '视频已生成完成',
                                'timestamp': time.time()
                            }
                            yield f"event: message\ndata: {json.dumps(progress_event, ensure_ascii=False)}\n\n"
                            update_socket_status(backend_key, 'done4_generate_video__1', user_id)  # 3min
                            break
                        else:
                            # 发送进度更新
                            status = res_data.get('status')
                            status_message = '未知状态...'
                            if status == 'pending':
                                status_message = '排队中...'
                            else:
                                retry_i += 1
                            if status == 'processing':
                                status_message = '正在生成中...'
                            if status == 'uploading':
                                status_message = '视频上传中...'
                            progress_event = {
                                'progress': progress_percent,
                                'message': status_message,
                                'details': result,
                                'timestamp': time.time()
                            }
                            yield f"event: message\ndata: {json.dumps(progress_event, ensure_ascii=False)}\n\n"
                            if retry_i > retry_break:
                                break
                    else:
                        log.warning(f"进度查询失败: HTTP {response.status_code}")
                        # 发送进度消息（即使查询失败也继续尝试）
                        progress_event = {
                            'progress': retry_i,
                            'message': '正在等待视频生成...',
                            'timestamp': time.time()
                        }
                        yield f"event: message\ndata: {json.dumps(progress_event, ensure_ascii=False)}\n\n"

                except requests.exceptions.Timeout:
                    log.warning(f"第{i + 2}次请求超时")
                    # 发送超时消息
                    progress_event = {
                        'progress': retry_i,
                        'message': '查询超时，继续等待...',
                        'timestamp': time.time()
                    }
                    yield f"event: message\ndata: {json.dumps(progress_event, ensure_ascii=False)}\n\n"

                except Exception as e:
                    log.error(f"第{i + 2}次请求出错: {str(e)}")
                    # 发送错误消息但继续尝试
                    progress_event = {
                        'progress': retry_i,
                        'message': f'查询出错: {str(e)[:50]}...',
                        'timestamp': time.time()
                    }
                    yield f"event: message\ndata: {json.dumps(progress_event, ensure_ascii=False)}\n\n"

                # 等待30秒后进行下一次查询（最后一次不等待）
                if i < max_retries - 1 and not video_url:
                    time.sleep(retry_interval)

            # 检查是否超时未完成
            if not video_url:
                log.warning("视频生成超时，未获取到视频URL")
                # 发送超时消息
                timeout_event = {
                    'progress': 100,
                    'message': '视频生成超时，请稍后手动检查',
                    'timestamp': time.time()
                }
                yield f"event: message\ndata: {json.dumps(timeout_event, ensure_ascii=False)}\n\n"

            # 发送结束事件
            end_event = {
                'status': 'completed',
                'timestamp': time.time(),
                'video_url': video_url,
                'message': '视频生成过程结束'
            }
            yield f"event: end\ndata: {json.dumps(end_event, ensure_ascii=False)}\n\n"
            update_socket_status(backend_key, 'done4_generate_video__2', user_id)  # 3min
            log.info(f"用户 {user_id} 视频生成请求完成，视频URL: {video_url}")

        except Exception as e:
            log.error(f"处理视频生成请求时出错: {str(e)}")
            error_event = {
                'error': str(e),
                'timestamp': time.time()
            }
            update_socket_status(backend_key, 'done4_generate_video__3', user_id)  # 3min
            yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        finally:
            update_socket_status(backend_key, 'done4_generate_video__4', user_id)  # 3min
            log.info(f"客户端 {user_id} 断开视频生成连接")

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route(f'/{backend_id}-{backend_name}/sse-generate-video', methods=['OPTIONS'])
def sse_generate_video_options():
    """处理视频生成预检请求"""
    return '', 200, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Methods': 'GET, OPTIONS'
    }


@app.route(f'/{backend_id}-{backend_name}/api/generate_time_sequence', methods=['POST', 'OPTIONS'])
def save_script():
    # 处理OPTIONS预检请求 跨域
    if request.method == 'OPTIONS':
        return '', 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        }

    # 处理POST请求
    data = request.get_json()
    if not data or 'video_id' not in data or 'script' not in data or 'user_id' not in data:
        return jsonify({"error": "缺少必要参数"}), 400
    video_id = data['video_id']
    user_id = data['user_id']
    update_socket_status(backend_key, 'busy3_generate_time_sequence', user_id)  # 3min

    # 生成文件名
    filename = f"{video_id}_{user_id}.txt"
    srt_file_path = get_srt_file_path(video_id)
    file_dir = os.path.dirname(srt_file_path)
    file_path = os.path.join(file_dir, filename)
    srt_path = os.path.join(file_dir, f'{video_id}.srt')
    # 保存文件
    try:
        if 'flag' in data and data['flag'] == 'debug':
            with open(file_path, 'r', encoding='utf-8') as f:
                wenan_content = f.read()
                result = get_keep_intervals(srt_path, wenan_content)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(data['script'])
                result = get_keep_intervals(srt_path, data['script'])

        ok_response = jsonify({
            "status": "success",
            "message": "脚本保存成功",
            "filename": filename,
            "result": result,
            "time_sequence": f"时间序列已保存到: {filename}"  # 可以根据需要生成真实的时间序列
        })

        # 设置CORS头
        ok_response.headers.add('Access-Control-Allow-Origin', '*')
        ok_response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        ok_response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        update_socket_status(backend_key, 'done3_generate_time_sequence__1', user_id)  # 3min
        return ok_response
    except Exception as e:
        error_response = jsonify({"error": f"文件保存失败: {str(e)}"})
        error_response.status_code = 500
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        update_socket_status(backend_key, 'done3_generate_time_sequence__2', user_id)  # 3min
        return error_response


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '接口不存在'}), 404


@app.errorhandler(500)
def internal_error(error):
    log.error(f"服务器内部错误: {str(error)}")
    return jsonify({'error': '服务器内部错误'}), 500


if __name__ == '__main__':
    # 从命令行参数获取端口，默认为5000


    log.info(f"启动 {backend_name} 服务，监听 0.0.0.0:{port}")

    # 启动Flask应用
    app.run(host='0.0.0.0', port=port)
