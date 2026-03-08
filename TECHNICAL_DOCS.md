# 智能视频分割系统 - 技术文档

## 1. 工程概述

### 1.1 项目简介

智能视频分割系统是一个基于 Flask 的 Web 服务平台，通过 AI 大模型分析视频字幕内容，根据用户提供的脚本/文案自动生成精确剪辑的视频片段。系统采用微服务架构，支持多后端实例并行处理请求。

**核心能力：**
- AI 聊天对话生成文案（SSE 流式输出）
- 文案与字幕智能匹配对齐
- 基于时间序列的视频自动剪辑
- 多任务队列和分布式处理

### 1.2 技术栈

| 层次 | 技术组件 |
|------|----------|
| Web 框架 | Flask + Flask-CORS |
| AI 模型 | DeepSeek API / 通义千问 (Bailian) |
| 视频处理 | FFmpeg / FFprobe |
| 实时通信 | SSE (Server-Sent Events) |
| 任务队列 | JSON 文件 + 轮询机制 |
| 日志系统 | Python logging (按天滚动) |
| 部署方式 | systemd 服务 (Linux) / 直接运行 (Windows) |

### 1.3 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           客户端 (前端)                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      API 网关层 (server.py:5000)                        │
│  - 静态资源服务  - SRT 文件上传  - 后端路由分发  - 用户认证              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
    ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
    │ backend1-16   │       │ backend1-16   │       │ backend1-16   │
    │ sse_server    │       │ sse_server    │       │ sse_server    │
    │ (5001-5016)   │       │ (5001-5016)   │       │ (5001-5016)   │
    │               │       │               │       │               │
    │ - SSE 聊天    │       │ - 时间序列    │       │ - 视频生成    │
    │ - 文案生成    │       │ - 字幕匹配    │       │ - 状态轮询    │
    └───────────────┘       └───────────────┘       └───────────────┘
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │  video_server.py (8868)       │
                    │  - 视频任务管理               │
                    │  - 任务队列维护               │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  run_video.py (工作线程)      │
                    │  - 轮询待处理任务             │
                    │  - FFmpeg 视频剪辑            │
                    │  - OSS 上传                   │
                    └───────────────────────────────┘
```

---

## 2. 核心模块说明

### 2.1 模块职责

| 文件 | 端口 | 职责 |
|------|------|------|
| `server.py` | 5000/80 | 主 API 服务器 - 文件上传下载、用户认证、后端路由 |
| `sse_server.py` | 5001+ | SSE 后端 - AI 聊天、时间序列生成、视频生成请求 |
| `video_server.py` | 8868 | 视频任务管理 - 任务队列、状态追踪 |
| `run_video.py` | - | 视频处理工作线程 - 轮询任务并执行 FFmpeg |
| `manager.py` | - | 进程健康监控 - 自动重启失败服务 |
| `config.py` | - | 配置管理 - API 密钥、SRT 解析、Token 计算 |
| `mylog.py` | - | 日志工具 - 统一的日志设置 |

### 2.2 make_time 模块 (AI 字幕匹配)

```
make_time/
├── step2.py      # 入口函数 get_keep_intervals()
├── mode2.py      # 文案解析和 AI 匹配核心逻辑
├── util.py       # AI 提示词生成、JSON 解析、时间轴处理
└── chat.py       # 多模型 AI 客户端 (DeepSeek/Bailian)
```

**核心流程：**
1. 解析用户文案为结构化段落
2. 提取 SRT 字幕为时间戳列表
3. 调用 AI 匹配文案句子到字幕片段
4. 相似度验证 (probability 校验)
5. 合并连续片段生成最终时间区间

### 2.3 make_video 模块 (视频处理)

```
make_video/
└── step3.py      # 视频剪辑核心逻辑
```

**处理流程：**
1. 提取 WAV 音频
2. 提取视频帧 (30fps)
3. 按时间区间切割音频
4. 按帧范围切割图片
5. 重组图片为视频
6. 合并音视频
7. 上传至 OSS

---

## 3. 数据流动

### 3.1 完整业务流程图

```mermaid
flowchart TD
    A[用户访问前端] --> B[server.py:5000<br/>主服务器]
    B --> C{请求类型}

    C -->|SRT 上传 | D[upload_srt]
    C -->|AI 聊天 | E[获取后端 URL]
    C -->|时间序列 | E
    C -->|视频生成 | E

    D --> D1[保存 SRT 到 static/download/srt]
    D1 --> D2[返回下载 URL]

    E --> F{后端状态}
    F -->|用户专属 done| G1[分配用户专属 backend]
    F -->|空闲 free| G2[分配空闲 backend]
    F -->|完成 done>3min| G3[分配最久完成的 backend]
    F -->|全 busy| H[等待或排队]

    G1 --> J[sse_server.py:5001+<br/>主服务器]
    G2 --> J
    G3 --> J

    J --> J1{SSE 端点}
    J1 -->|sse-chat| K[AI 文案生成]
    J1 -->|sse-chat-v2| L[脚本优化]
    J1 -->|api/generate_time_sequence| M[字幕匹配 AI]
    J1 -->|sse-generate-video| N[视频生成请求]

    K --> K1[DeepSeek API]
    K1 --> K2[SSE 流式返回前端]

    L --> L1[DeepSeek API]
    L1 --> L2[SSE 流式返回前端]

    M --> M1[解析 SRT 文件]
    M1 --> M2[AI 匹配文案到字幕]
    M2 --> M3[返回 keep_intervals]

    N --> N1[POST video_server:8868<br/>执行机 1 或执行机 2]
    N1 --> N2[user_task.json]
    N2 --> N3[SSE 轮询进度]

    O[run_video.py 轮询<br/>执行机] --> O1[读取 user_task.json]
    O1 --> O2{status=pending?}
    O2 -->|是 | O3[执行视频剪辑]
    O2 -->|否 | O1

    O3 --> P[extract_audio WAV]
    P --> Q[cut_and_merge_video_img<br/>帧级别切割]
    Q --> R[合并音视频]
    R --> S[ossutil 上传 OSS]
    S --> T[更新 status=completed + oss_path]

    N3 --> V{status=completed?}
    V -->|是 | W[返回 OSS URL]
    V -->|否 | N3
```

**架构说明**:
- **主服务器**: server.py (API 网关) + sse_server x16 (AI 处理) + manager.py + up_status.py
- **执行机**: video_server.py + run_video.py (可部署多台，当前配置 2 台)
- **后端分配逻辑** (server.py `/api/get_backend_url`):
  1. 优先分配用户专属 backend (done 状态)
  2. 其次分配空闲 backend (free 状态)
  3. 再次分配完成超过 3 分钟的 backend (done 状态)
  4. 最后分配最久完成的 busy backend
```

### 3.2 状态流转图

```mermaid
stateDiagram-v2
    [*] --> pending: 创建任务
    pending --> processing: run_video 拾取
    processing --> uploading: 视频剪辑完成 (cut_video_main)
    uploading --> completed: OSS 上传成功
    completed --> [*]

    note right of pending
        等待工作线程处理
        user_task.json 中 status=pending
    end note

    note right of processing
        FFmpeg 切割中
        1. extract_audio (提取 WAV)
        2. cut_and_merge_video_img (帧级别切割)
        3. 合并音视频
    end note

    note right of uploading
        ossutil 上传到 OSS
        upload_video() 执行
    end note

    note right of completed
        oss_path 已写入
        前端可下载视频 URL
    end note
```

**状态更新流程 (run_video.py 主循环)**:
```
update_task_status(user_id, video_id, "processing")  # 开始处理
  → cut_video_main()                                  # 执行 FFmpeg
  → update_task_status(user_id, video_id, "uploading") # 开始上传
  → upload_video()                                    # ossutil 上传
  → update_task_status(user_id, video_id, "completed", oss_path) # 完成
```

---

## 4. 代码逻辑关系

### 4.1 模块依赖关系图

```mermaid
graph TD
    subgraph Web 层 - 主服务器
        server[server.py:5000/80]
        sse[sse_server.py:5001-5016<br/>16 个后端实例]
        manager[manager.py<br/>进程监控]
        up_status[up_status.py<br/>状态清理]
    end

    subgraph 执行机 - 视频处理服务器
        video[video_server.py:8868<br/>任务管理]
        run_video[run_video.py<br/>工作线程]
    end

    subgraph 工具模块
        config[config.py]
        mylog[mylog.py]
    end

    subgraph make_time - AI 字幕匹配
        step2[step2.py<br/>入口函数]
        mode2[mode2.py<br/>文案解析/AI 匹配]
        util[util.py<br/>提示词/JSON 解析]
        chat[chat.py<br/>DeepSeek/Bailian]
    end

    subgraph make_video - FFmpeg 处理
        step3[step3.py<br/>切割/合并]
    end

    %% 主服务器依赖
    server --> config
    server --> mylog
    server --> sse

    %% SSE 后端依赖
    sse --> config
    sse --> mylog
    sse --> step2
    sse --> video

    %% 执行机依赖
    video --> config
    video --> step3

    run_video --> config
    run_video --> step3

    %% make_time 内部依赖
    step2 --> mode2
    step2 --> util
    mode2 --> util
    mode2 --> chat
    util --> chat

    %% make_video 依赖
    step3 --> config

    %% 监控依赖
    manager --> server
    manager --> sse

    up_status --> sse
```

**部署架构说明**:
| 组件 | 部署位置 | 说明 |
|------|----------|------|
| server.py | 主服务器 | API 网关、文件上传下载 |
| sse_server.py | 主服务器 | 16 个后端实例 (端口 5001-5016) |
| manager.py | 主服务器 | 进程健康监控 |
| up_status.py | 主服务器 | 清理超时后端状态 |
| video_server.py | 执行机 (可多台) | 视频任务管理 (端口 8868) |
| run_video.py | 执行机 (可多台) | 视频处理工作线程 |
```

### 4.2 API 调用时序图

```mermaid
sequenceDiagram
    participant Client as 前端客户端
    participant Gateway as server.py:5000<br/>(主服务器)
    participant Backend as sse_server:5001<br/>(主服务器)
    participant VideoSrv as video_server:8868<br/>(执行机)
    participant Worker as run_video.py<br/>(执行机)
    participant DeepSeek as DeepSeek API
    participant OSS as OSS 存储

    Client->>Gateway: POST /api/get_backend_url
    Gateway-->>Client: backend_url=http://:5001
    Gateway->>Gateway: 分配后端 (专属→空闲→最久完成)

    Client->>Backend: GET /sse-chat?prompt=xxx
    Backend->>DeepSeek: Chat Completion API
    DeepSeek-->>Backend: Stream Response
    Backend-->>Client: SSE Events

    Client->>Backend: POST /api/generate_time_sequence
    Backend->>Backend: 解析 SRT
    Backend->>DeepSeek: AI 匹配请求 (JSON 格式)
    DeepSeek-->>Backend: JSON id_list
    Backend-->>Client: keep_intervals

    Client->>Backend: GET /sse-generate-video
    Backend->>VideoSrv: POST /make_video (执行机 1/2)
    VideoSrv-->>Backend: task_id
    VideoSrv->>VideoSrv: 写入 user_task.json
    Backend-->>Client: SSE progress:0%

    loop 轮询 (30s 间隔)
        Worker->>Worker: 读取 user_task.json
        Worker->>Worker: status=pending?
        Worker->>Worker: cut_video_main
        Worker->>Worker: ffmpeg 切割
        Worker->>OSS: ossutil 上传
        Worker->>VideoSrv: 更新 status=completed
        Backend->>VideoSrv: GET /get_task
        VideoSrv-->>Backend: status=processing/uploading
        Backend-->>Client: SSE progress:N%
    end

    Worker->>VideoSrv: status=completed + oss_path
    Backend->>VideoSrv: GET /get_task
    VideoSrv-->>Backend: oss_path
    Backend-->>Client: SSE video_url + complete
```

**执行机说明**:
- 代码中 `servers = ["113.249.107.180", "113.249.107.182"]` 定义了两个执行机 IP
- `sse_generate_video()` 会遍历执行机列表，选择第一个成功响应的服务器
- 每个执行机运行独立的 `video_server.py` 和 `run_video.py`
- 任务队列 `user_task.json` 在每个执行机上独立维护
```

---

## 5. 关键路径说明

### 5.1 路径 1: AI 文案生成 (sse-chat)

```
前端 → server.py (获取后端) → sse_server.py → DeepSeek API → SSE 返回
```

**关键代码：**
- `sse_server.py:168-247` - sse_chat() 端点
- `sse_server.py:127-157` - llm_generate_stream() 流式生成
- `chat.py:10-60` - ask_ai() 多模型路由

**后端状态变更：**
`free` → `busy1_sse_chat` → `done1_sse_chat__1/2/3` (3 分钟超时)

**详细流程：**
1. 前端访问 server.py 获取后端 URL
2. server.py 查询 `socket_status.json` 分配后端
3. 前端请求 SSE 聊天接口
4. sse_server 更新状态为 `busy1_sse_chat`
5. 调用 DeepSeek API 流式生成
6. SSE 逐块返回文本给前端
7. 完成后更新状态为 `done1_sse_chat__1/2/3`

### 5.2 路径 2: 时间序列生成 (字幕匹配)

```
前端提交文案 → sse_server.py → 解析 SRT → AI 匹配 → 返回 keep_intervals
```

**关键代码：**
- `sse_server.py:588-643` - save_script() 端点
- `make_time/step2.py:39-43` - get_keep_intervals()
- `make_time/mode2.py:12-105` - get_yuanwen_mode2() 文案解析
- `make_time/mode2.py:109-269` - get_intervals_by_yuanwen() 字幕匹配
- `make_time/util.py:265-293` - get_unit_interval_by_ai() AI 相似度校验

**后端状态变更：**
`free` → `busy3_generate_time_sequence` → `done3_...` (3 分钟超时)

**详细流程：**
1. 前端 POST 文案到 `/api/generate_time_sequence`
2. sse_server 更新状态为 `busy3_generate_time_sequence`
3. 读取 SRT 文件并解析为 `zimu_list`
4. 解析文案为 `yuanwen` 结构 (带时间轴和文本)
5. 对每个文案句子调用 AI 匹配到字幕片段
6. AI 返回 `id_list` 并进行二次校验 (probability)
7. 合并连续片段生成 `keep_intervals`
8. 返回 JSON 结果给前端

### 5.3 路径 3: 视频生成

```
前端 → sse_server → video_server (创建任务) → run_video 轮询 → FFmpeg → OSS
```

**关键代码：**
- `sse_server.py:355-575` - sse_generate_video() SSE 流
- `sse_server.py:328-352` - execute_on_server() 执行机选择
- `video_server.py:64-167` - make_video() 创建任务
- `run_video.py:208-225` - 主循环轮询
- `run_video.py:218-224` - cut_video_main + upload_video
- `make_video/step3.py:355-361` - cut_video_main()
- `make_video/step3.py:167-218` - cut_and_merge_video_img() 无损切割

**任务状态变更：**
`pending` → `processing` → `uploading` → `completed`

**后端状态变更：**
`free` → `busy4_generate_video` → `done4_...` (15 分钟超时)

**详细流程：**
1. 前端 GET `/sse-generate-video` 发起请求
2. sse_server 更新状态为 `busy4_generate_video`
3. 遍历执行机列表 (`servers` 数组)
4. POST `/make_video` 到 video_server:8868
5. video_server 写入 `user_task.json` (status=pending)
6. run_video 轮询发现 pending 任务
7. 更新状态为 `processing`
8. 执行 `cut_video_main()`:
   - `extract_audio()` 提取 WAV 音频
   - `cut_and_merge_video_img()` 帧级别切割视频
   - 合并音视频为 MP4
9. 更新状态为 `uploading`
10. `upload_video()` 使用 ossutil 上传
11. 更新状态为 `completed` + oss_path
12. sse_server 轮询到完成状态，返回 video_url

**SSE 进度轮询：**
```
progress:0 → waiting... (30s 间隔)
→ pending:排队中...
→ processing:正在生成中... (retry_i++)
→ uploading:视频上传中...
→ 100%:视频已生成完成 + video_url
```

---

## 6. 配置文件结构

### 6.1 config.yaml (API 密钥)

```yaml
DEEPSEEK_API_KEY: sk-xxxx
BAILIAN_API_KEY: sk-xxxx
```

### 6.2 config.json (用户配置)

```json
{
  "token_list": ["token1", "token2", ...],
  "name_dic": {
    "001": "c0929290...-backend1",
    "002": "...-backend2",
    ...
  }
}
```

### 6.3 socket_status.json (后端状态)

```json
{
  "001": {
    "status": "free|busy1_sse_chat|done1_sse_chat__1|...",
    "cur_time": 1709712345.678,
    "user_id": "001",
    "update_time": "2026-03-07 10:30:45"
  }
}
```

### 6.4 user_task.json (视频任务队列)

```json
[
  {
    "video_id": "C1872",
    "user_id": "001",
    "keep_intervals": [["00:01:00,000", "00:02:30,500"], ...],
    "created_at": "2026-03-07 10:00:00",
    "status": "pending|processing|uploading|completed",
    "oss_path": "http://video.kaixin.wiki/..."
  }
]
```

---

## 7. 核心数据结构

### 7.1 SRT 解析结构

```python
# zimu_list 格式
[
    [序号，[开始时间，结束时间], 文本],
    [104, ["00:03:25,100", "00:03:27,833"], "真正的你要知道敌人是什么"],
    ...
]
```

### 7.2 keep_intervals 结构

```python
# 时间区间列表 (时间字符串格式)
[
    [cut_start, cut_end, id_list, yuan_text, zimu_mode],
    ["00:01:00,000", "00:02:30,500", [100,101,102], "原文句子", 0],
    ...
]

# 合并后的结构 (用于 FFmpeg)
[
    [[start, end], text],
    [["00:01:00,000", "00:02:30,500"], "合并的文本"],
    ...
]
```

### 7.3 文案解析结构 (yuanwen)

```python
[
    {
        'part_name': '观点',
        'part_text': '企业扩张时要学会就地取材',
        'part_time': ['00:01:00', '00:02:00'],
        'zimu_list': [
            {'time_text': '00:01:00,000 --> 00:01:05,000',
             'start': '00:01:00,000',
             'end': '00:01:05,000',
             'text': '企业扩张时'}
        ]
    }
]
```

---

## 8. 部署架构

### 8.1 systemd 服务配置

```ini
# /etc/systemd/system/backend1.service
[Unit]
Description=Backend Server 1
After=network.target

[Service]
User=root
WorkingDirectory=/root/ttt
ExecStart=/usr/bin/python3 sse_server_backend1.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 8.2 服务列表

| 服务名 | 端口 | 数量 |
|--------|------|------|
| app/server | 80/5000 | 1 |
| sse_server | 5001-5016 | 16 |
| video_server | 8868 | 1-2 |
| run_video | - | 1-2 |
| manager | - | 1 |
| up_status | - | 1 |

---

## 9. 性能优化点

### 9.1 Token 分割
当 SRT 文件超过 `limit_prompt (8192 tokens)` 时自动分割为多个部分处理。

### 9.2 文件锁机制
Linux 上使用 `fcntl.flock()` 实现 JSON 文件的并发访问控制。

### 9.3 后端负载均衡
通过 `socket_status.json` 实现请求分发：
1. 优先分配用户专属后端
2. 其次分配空闲后端
3. 最后分配完成时间最久的 busy 后端

### 9.4 FFmpeg 优化
- 使用无损切割避免重新编码
- 帧级别精确剪辑
- 先切割后合并策略

---

## 10. 错误处理

### 10.1 AI API 错误
- DeepSeek 调用失败时返回错误 SSE 事件
- 相似度校验失败 (probability < 0.88) 时标记为无效区间

### 10.2 任务队列错误
- JSONDecodeError 时初始化为空数组/字典
- 文件锁获取失败时抛出 RuntimeError

### 10.3 视频处理错误
- FFmpeg 命令失败时抛出 CalledProcessError
- OSS 上传失败时保持任务状态为 uploading

---

## 11. 监控与维护

### 11.1 健康检查端点
- `GET /health_check` - server.py
- `GET /health_check` - sse_server.py (各 backend)
- `GET /health` - video_server.py

### 11.2 日志文件
- `logs/app/log.txt` - 主服务器日志
- `logs/backendN/backendN.txt` - 各后端日志
- `/var/log/backend/*.log` - systemd 服务日志

### 11.3 自动重启
`manager.py` 每 2 秒检查各服务健康状态，失败时自动重启。

`up_status.py` 每 30 秒清理超时任务状态 (busy4 超过 100 分钟/其他超过 15 分钟)。

---

## 附录 A：API 端点汇总

| 端点 | 方法 | 服务器 | 说明 |
|------|------|--------|------|
| `/upload_srt` | POST | server.py | 上传 SRT 文件 |
| `/api/get_backend_url` | POST | server.py | 获取后端 URL |
| `/{id}-{name}/sse-chat` | GET | sse_server | AI 聊天流 |
| `/{id}-{name}/sse-chat-v2` | GET | sse_server | 脚本优化流 |
| `/{id}-{name}/api/generate_time_sequence` | POST | sse_server | 生成时间序列 |
| `/{id}-{name}/sse-generate-video` | GET | sse_server | 视频生成流 |
| `/make_video` | POST | video_server | 创建视频任务 |
| `/get_task` | POST | video_server | 查询任务状态 |
| `/tasks` | GET | video_server | 任务列表 |

---

*文档生成时间：2026-03-07*
