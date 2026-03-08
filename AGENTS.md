# AGENTS.md - 开发指南

## 构建/运行命令

### Windows 开发环境运行服务
```bash
# 主服务器（API 网关）
python server.py

# SSE 后端实例（可运行多个，不同端口）
python sse_server.py 5001 backend1 <backend_id> <backend_key>

# 视频任务服务器（工作机器）
python video_server.py

# 视频处理工作进程（工作机器）
python run_video.py

# 进程监控（主服务器）
python manager.py

# 状态清理（主服务器）
python up_status.py
```

### Linux 生产环境（systemd）
```bash
# 查看服务状态
systemctl status backend1

# 重启服务
systemctl restart backend1

# 查看日志
journalctl -u backend1 -f
```

### 测试说明
本项目无正式测试框架，手动测试方法：
1. 启动所需服务
2. 向端点发送 HTTP 请求
3. 检查 `logs/` 目录查看输出

## 代码风格指南

### 导入规范
- 标准库导入优先（`os`、`sys`、`json`、`time`）
- 第三方导入其次（`flask`、`requests`、`openai`）
- 本地导入最后（`mylog`、`config`、`make_time.step2`）
- 可选模块使用 `try/except ImportError` 包裹（如 `fcntl`）

### 命名约定
- **变量**: snake_case（如 `backend_key`、`user_id`、`srt_path`）
- **函数**: snake_case（如 `get_keep_intervals`、`update_socket_status`）
- **类**: PascalCase（如 `Config`）
- **常量**: 全大写下划线（如 `LIMIT_PROMPT`、`HLS_DIR`）
- **全局变量**: 使用 `glo_` 或 `glo_dic` 前缀

### 代码格式
- 无严格强制，但遵循现有模式
- 行续行：使用反斜杠或隐式括号
- 最大行长：约 120 字符（非强制）
- 缩进：4 个空格（不使用 Tab）

### 类型注解
- 本项目不使用类型注解
- 优先使用鸭子类型
- 错误时返回 `None`，成功时返回有效数据

### 错误处理
```python
# 模式 1: try/except 加日志
try:
    data = json.load(f)
except json.JSONDecodeError:
    print(f'JSONDecodeError')
    data = {}

# 模式 2: 失败时返回 False/None
def some_function():
    try:
        # ...
        return True
    except Exception as e:
        print(f'Error: {str(e)}')
        return False
```
- 使用 `print()` 记录日志（大多数模块不使用正式 logging）
- 使用 `mylog.setup_logger()` 共享日志器
- 优先提前返回而非抛出异常

### 文件操作
```python
# 始终使用 UTF-8 编码
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Linux 上使用 fcntl 文件锁处理并发 JSON 访问
if not is_windows():
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
# ... 操作 ...
fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

### 函数设计
- 小型、专注的函数（大多数少于 50 行）
- 使用全局字典（`glo_dic`、`data_dic`）共享状态
- 传递路径作为参数，避免硬编码字符串
- 使用 `os.path.join()` 处理跨平台路径

### 日志记录
```python
# 设置共享日志器
log = mylog.setup_logger('logs/app', 'log.txt')
log.info(f'value={value}')

# 简单调试使用 print()
print(f'cmd={cmd}')
```

### API 设计
- REST 端点通过 `jsonify()` 返回 JSON
- 使用 `request.get_json()` 获取 POST 请求体
- SSE 端点返回带 `text/event-stream` 的 `Response`
- 错误响应：`{"error": "消息"}` 加 HTTP 状态码

### 常见代码模式

**SRT 字幕解析:**
```python
def parse_zimu_content(content):
    result = []
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        if lines[i].strip().isdigit():
            # 处理字幕块
            ...
            i += 3
        else:
            i += 1
    return result
```

**FFmpeg 子进程调用:**
```python
cmd = ["ffmpeg", "-i", input_file, "-c:v", "copy", output_file]
subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
```

**任务队列（基于 JSON 文件）:**
```python
# 加锁读取
with open('user_task.json', 'r+', encoding='utf-8') as f:
    if not is_windows():
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    tasks = json.load(f)
    # 查找待处理任务
    for task in tasks:
        if task.get('status') == 'pending':
            process(task)
            task['status'] = 'completed'
            break
    f.seek(0)
    f.truncate()
    json.dump(tasks, f, ensure_ascii=False, indent=2)
```

### 跨平台兼容
```python
# 检查操作系统
if is_windows():
    # Windows 专用代码
else:
    # Linux 专用代码（如 fcntl 文件锁）
```

### 安全注意事项
- 切勿提交 `data/config/config.yaml`（包含 API 密钥）
- 通过 config 中的 `upload_token` 进行令牌验证
- 所有用户输入在文件操作前必须验证

### 项目依赖
- Flask, Flask-CORS（Web 框架）
- openai（AI 客户端 SDK）
- transformers（本地分词器）
- requests（HTTP 客户端）
- PyYAML（配置解析）
- FFmpeg/FFprobe（系统命令处理视频）
- ossutil（OSS 上传，仅 Linux）
