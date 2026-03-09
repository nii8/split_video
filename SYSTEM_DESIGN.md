# 智能视频分割系统 - 系统设计文档

> 本文档由代码交叉验证生成，以代码为唯一事实依据。
> 覆盖 ARCHITECTURE.md 和 TECHNICAL_DOCS.md 全部内容，两者不再单独维护。
> 生成时间：2026-03-09

---

## 1. 概述

智能视频分割系统是基于 Flask 的 Web 服务平台，通过 AI 大模型分析视频字幕，根据用户提供的文案脚本自动生成精确剪辑的视频片段。

**核心能力：**
- SSE 流式 AI 对话生成文案（DeepSeek API）
- 文案与字幕两阶段 AI 智能匹配对齐
- 基于时间序列的 FFmpeg 无损视频剪辑
- 多后端负载均衡 + 分布式执行机处理

**技术栈：**

| 层次 | 技术组件 |
|------|----------|
| Web 框架 | Flask + Flask-CORS |
| AI 模型 | DeepSeek API / 阿里云 Bailian (通义千问) |
| 视频处理 | FFmpeg / FFprobe + ossutil |
| 实时通信 | SSE (Server-Sent Events) |
| 任务队列 | JSON 文件 + fcntl 文件锁 + 轮询 |
| 日志系统 | Python logging（TimedRotatingFileHandler，按天滚动）|
| 部署方式 | systemd（Linux）/ 直接运行（Windows 开发） |

---

## 2. 部署架构

### 2.1 物理架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      主服务器 (Master)                           │
│                                                                  │
│  server.py (80/5000)     sse_server.py × 16 (5001-5016)         │
│  API 网关                SSE 后端（AI 处理）                     │
│                                                                  │
│  manager.py              up_status.py                            │
│  进程监控（pkill）        状态超时清理                            │
│                                                                  │
│  共享：./data/config/socket_status.json                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP (POST /make_video, GET /get_task)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   执行机 (Worker) × N                            │
│                                                                  │
│  video_server.py (8868)       run_video.py                       │
│  任务 API 管理                视频处理工作线程（轮询）            │
│                                                                  │
│  独立：user_task.json（各执行机独立维护）                        │
│  视频数据：./data/hanbing/**（SRT + MP4 + JSON）                 │
└─────────────────────────────────────────────────────────────────┘
                               │ ossutil cp
                               ▼
                    ┌─────────────────────┐
                    │   OSS 对象存储       │
                    │ video.kaixin.wiki    │
                    └─────────────────────┘
```

### 2.2 主从职责边界

| 职责 | 主服务器 | 执行机 |
|------|---------|--------|
| 用户认证（token 验证）| ✅ server.py | ❌ |
| AI 对话 / SSE 流式输出 | ✅ sse_server.py | ❌ |
| 文案-字幕 AI 匹配 | ✅ sse_server.py | ❌ |
| 后端负载均衡分配 | ✅ server.py | ❌ |
| 进程健康监控 | ✅ manager.py | ❌ |
| 状态超时清理 | ✅ up_status.py | ❌ |
| 视频任务 API 管理 | ❌ | ✅ video_server.py |
| FFmpeg 视频剪辑 | ❌ | ✅ run_video.py |
| OSS 上传 | ❌ | ✅ run_video.py |
| SRT 文件发送方 | 接收端（/upload_video_srt）| 发送端（get_new_video 时）|

### 2.3 模块依赖关系

```mermaid
graph TB
    subgraph Master["主服务器"]
        server["server.py\n端口 5000/80\nAPI 网关"]
        sse["sse_server.py\n端口 5001-5016\n16 个 SSE 实例"]
        manager["manager.py\n进程监控"]
        up_status["up_status.py\n状态清理"]
        socket_json["socket_status.json\n后端共享状态"]
    end

    subgraph Worker["执行机"]
        videoserver["video_server.py\n端口 8868\n任务管理"]
        runvideo["run_video.py\n视频处理"]
        user_task["user_task.json\n任务队列"]
    end

    subgraph MakeTime["make_time（AI 字幕匹配）"]
        step2["step2.py\n入口 get_keep_intervals()"]
        mode2["mode2.py\n文案解析 / AI 匹配"]
        util["util.py\n提示词 / 相似度验证"]
        chat["chat.py\nDeepSeek / Bailian 客户端"]
    end

    subgraph MakeVideo["make_video（视频处理）"]
        step3["step3.py\n无损切割 / 音视频合并"]
    end

    subgraph Common["公共模块"]
        config["config.py\n配置 / SRT 解析 / Token 计算"]
        mylog["mylog.py\n日志工具"]
    end

    subgraph External["外部服务"]
        deepseek["DeepSeek API\napi.deepseek.com"]
        bailian["Bailian API\ndashscope.aliyuncs.com"]
        oss["OSS\nvideo.kaixin.wiki"]
    end

    server --> config
    server --> mylog
    server -.->|读写| socket_json

    sse --> config
    sse --> mylog
    sse --> step2
    sse -.->|读写| socket_json
    sse -->|POST /make_video\nGET /get_task| videoserver

    manager -.->|HTTP 健康检查 + pkill| server
    manager -.->|HTTP 健康检查 + pkill| sse
    up_status -.->|超时重置为 free| socket_json

    videoserver --> config
    videoserver -->|写入| user_task
    runvideo -.->|轮询 + 直接读写| user_task
    runvideo --> step3
    runvideo --> config
    runvideo -->|ossutil cp| oss
    runvideo -->|POST /upload_video_srt| server

    step2 --> mode2
    mode2 --> util
    util --> chat
    chat --> deepseek
    chat --> bailian

    step3 --> config
```

---

## 3. 完整数据流（时序图）

```mermaid
sequenceDiagram
    autonumber
    participant Client as 前端客户端
    participant Gateway as server.py:5000
    participant SSE as sse_server.py:500X
    participant VideoSrv as video_server.py:8868
    participant Worker as run_video.py
    participant DeepSeek as DeepSeek API
    participant OSS as OSS 存储

    rect rgb(230, 240, 255)
        note over Client,Gateway: 阶段 0：获取后端 URL
        Client->>Gateway: POST /api/get_backend_url {video_id, token}
        Gateway->>Gateway: 读取 socket_status.json
        Gateway->>Gateway: 优先级分配：用户专属done → free → 最久idle
        Gateway-->>Client: {backend_url, user_id}
    end

    rect rgb(230, 255, 230)
        note over Client,SSE: 阶段 1：AI 文案生成（sse-chat）
        Client->>SSE: GET /{id}-{name}/sse-chat?prompt&video_id&user_id
        SSE->>SSE: update socket_status → busy1_sse_chat
        SSE->>SSE: 读取 SRT 文件，计算 token 长度
        SSE->>SSE: 超限则 split_srt_content() 分割
        SSE->>DeepSeek: Chat Completion（stream=True）
        DeepSeek-->>SSE: 流式 chunks
        SSE-->>Client: SSE events {start / message / end}
        SSE->>SSE: update socket_status → done1_sse_chat__X
    end

    rect rgb(255, 245, 220)
        note over Client,SSE: 阶段 2：脚本优化（sse-chat-v2，可选）
        Client->>SSE: GET /{id}-{name}/sse-chat-v2?prompt&video_id&user_id
        SSE->>SSE: update → busy2_sse_chat_v2
        SSE->>DeepSeek: Chat Completion（stream=True）
        DeepSeek-->>SSE: 流式 chunks
        SSE-->>Client: SSE events
        SSE->>SSE: update → done2_sse_chat_v2__X
    end

    rect rgb(255, 230, 230)
        note over Client,SSE: 阶段 3：时间序列生成（字幕匹配）
        Client->>SSE: POST /{id}-{name}/api/generate_time_sequence {script, video_id, user_id}
        SSE->>SSE: update → busy3_generate_time_sequence
        SSE->>SSE: get_keep_intervals(srt_path, script)
        SSE->>SSE: 解析文案段落 get_yuanwen_mode2()
        loop 每个文案句子
            SSE->>DeepSeek: AI 匹配请求（JSON 格式，第1次）
            DeepSeek-->>SSE: {id_list, text}
            SSE->>DeepSeek: 相似度验证（第2次，get_check_promot）
            DeepSeek-->>SSE: {probability}
            SSE->>SSE: probability < 0.88 → 降级 get_intervals_by_ai_find()
        end
        SSE->>SSE: merge_intervals() 合并连续区间
        SSE-->>Client: {keep_intervals, merged_intervals}
        SSE->>SSE: update → done3_generate_time_sequence__X
    end

    rect rgb(220, 255, 255)
        note over Client,OSS: 阶段 4：视频生成（sse-generate-video）
        Client->>SSE: GET /{id}-{name}/sse-generate-video?data={video_id,user_id,keep_intervals}
        SSE->>SSE: update → busy4_generate_video

        loop 遍历 servers 列表直到成功
            SSE->>VideoSrv: POST /make_video {video_id, user_id, keep_intervals}
            VideoSrv->>VideoSrv: 写入 user_task.json (status=pending)
            VideoSrv-->>SSE: {task_id}
        end
        SSE-->>Client: SSE progress:0% 任务已启动

        Note over Worker: run_video.py 独立轮询（每10秒）
        Worker->>Worker: get_first_pending_task()
        Worker->>Worker: update_task_status → processing（直接写 user_task.json）
        Worker->>Worker: extract_audio() 提取 WAV（已存在则跳过）
        Worker->>Worker: cut_and_merge_audio() 切割音频片段
        Worker->>Worker: cut_and_merge_video_img() ffmpeg concat 无损切割
        Worker->>Worker: ffmpeg 合并音视频（-c:v copy -c:a aac）
        Worker->>Worker: update_task_status → uploading（直接写 user_task.json）
        Worker->>OSS: ossutil cp 上传 MP4
        Worker->>Worker: update_task_status → completed + oss_path（直接写 user_task.json）

        loop SSE 轮询进度（每30秒，最多99次）
            SSE->>VideoSrv: POST /get_task {user_id, video_id}
            VideoSrv->>VideoSrv: 读取 user_task.json
            VideoSrv-->>SSE: {status, oss_path}
            SSE-->>Client: SSE progress:N%
        end
        SSE-->>Client: SSE event:video_url {video_url}
        SSE->>SSE: update → done4_generate_video__X
    end
```

> **关键说明**
> - `run_video.py` 通过 `update_task_status()` **直接读写** `user_task.json`，不调用 `video_server.py` 的任何 API
> - `sse_server.py` 发起 `/make_video` 请求，**不是** `server.py`
> - `run_video.py` 轮询 `video_list.json` 发现新视频时，调用 `send_srt()` 上传 SRT 到主服务器，此时帧提取命令处于注释状态，SRT 同步独立执行

---

## 4. 核心模块详解

### 4.1 server.py — API 网关

**后端分配逻辑** (`get_backend_url`)，优先级从高到低：

```
1. 该 user_id 已有 done 状态的后端（专属复用）
2. 该 user_id 已有 free 状态的后端
3. 任意 free 状态后端
4. done 状态超过 180 秒、且空闲最久的后端（抢占）
5. 以上均不满足 → 返回 backend_status=busy
```

### 4.2 sse_server.py — SSE 后端

每个实例通过命令行参数启动，路由动态绑定：

```bash
python sse_server.py [port] [backend_name] [backend_id] [backend_key]
# 示例：
python sse_server.py 5001 backend1 c0929290-6d79-40de-af54-e8aae8072060 001
```

- `backend_id`（UUID）+ `backend_name` 共同构成路由前缀：`/{backend_id}-{backend_name}/`
- `backend_key`（如 `001`）用于读写 `socket_status.json` 中的对应条目

### 4.3 make_time — AI 字幕匹配

```mermaid
flowchart TD
    Start[get_keep_intervals\nsrt_path + script] --> ParseScript[解析用户文案\nget_yuanwen_mode2]
    ParseScript --> ParseSRT[解析 SRT\nparse_zimu_content]

    subgraph ScriptFormat["文案支持格式"]
        F1["带时间段落标题\n观点：xxx（00:02:15-00:05:15）"]
        F2["无时间段落标签\n观点：/ 解释：/ 故事：/ 出路："]
        F3["省略号拆分\n句子A...句子B → 两条独立匹配"]
    end

    ParseScript --> ScriptFormat

    subgraph AILoop["AI 两阶段匹配（每个文案句子）"]
        G1[生成匹配提示词\nget_id_list_promot_mode2] --> G2[第1次 AI 调用\n返回 id_list + text]
        G2 --> G3[生成验证提示词\nget_check_promot]
        G3 --> G4[第2次 AI 调用\n返回 probability]
        G4 --> G5{probability > 0.88\n连续 id +0.05}
        G5 -->|通过| G6[保留时间区间]
        G5 -->|未通过| G7[降级全文搜索\nget_intervals_by_ai_find]
        G7 --> G6
    end

    ParseSRT --> AILoop
    G6 --> Merge[合并连续区间\nmerge_intervals]
    Merge --> Output["输出\n{keep_intervals, merged_intervals}"]
```

**`keep_intervals` 数据格式（贯穿全流程）：**

```python
# merge_intervals() 输出 / user_task.json 存储格式
[
    [["00:01:00,000", "00:02:30,500"], "合并后的文本"],
    [["00:03:10,200", "00:04:05,800"], "下一段文本"],
]

# step3.ffmpeg_cut_mp4 内部转换为浮点秒后传入 cut_and_merge_*
# unit[0][0] → time_str_to_seconds() → float
```

### 4.4 make_video/step3.py — 视频处理

**当前实际流程（无损切割方案）：**

```mermaid
flowchart TD
    Start["cut_video_main\nkeep_intervals, video_path"] --> E1["extract_audio()\n提取 WAV\n已存在则跳过"]
    E1 --> A1["cut_and_merge_audio()\n按区间切割音频片段\nffmpeg -ss -to + concat"]
    E1 --> V1["cut_and_merge_video_img()\nffmpeg concat 无损切割"]
    V1 --> V2["生成 clip_list.txt\nfile + inpoint + outpoint"]
    V2 --> V3["ffmpeg concat\n-c:v copy -c:a copy"]
    A1 --> M1["ffmpeg 合并音视频\n-c:v copy -c:a aac"]
    V3 --> M1
    M1 --> Done[输出 MP4]
```

> **注意**：`cut_and_merge_img()`（帧提取旧方案）仍存在于文件中但未被调用，帧提取相关代码在 `run_video.py` 中也已注释。

### 4.5 run_video.py — 执行机工作线程

**主循环逻辑：**

```python
while True:
    get_new_video()          # 检测新视频 → 发送 SRT 到主服务器
    task = get_first_pending_task()
    if task:
        update_task_status(user_id, video_id, "processing")   # 直接写 JSON
        cut_video_main(keep_intervals, video_path, ...)
        update_task_status(user_id, video_id, "uploading")    # 直接写 JSON
        oss_path = upload_video(video_path, video_id, user_id)
        update_task_status(user_id, video_id, "completed", oss_path)
    time.sleep(10)
```

### 4.6 manager.py — 进程监控

```python
# manager.py 的实际行为
subprocess.run(["pkill", "-9", "-f", f"python3 {process_name}"])
time.sleep(30)
# 无 Popen / subprocess.Popen，依赖 systemd Restart=always 自动拉起
```

> **重要**：manager.py 只负责 `pkill` 杀死异常进程，不负责拉起新进程。依赖 systemd 的 `Restart=always` 配置完成重启。在非 systemd 环境（Windows 开发机）pkill 失败后进程不会被重新拉起。

### 4.7 up_status.py — 状态超时清理

每 **30 秒**扫描 `socket_status.json`，超时则重置为 `free`：

| 状态 | 超时阈值 |
|------|----------|
| `busy1/2/3` 或 `done1/2/3` | **15 分钟** |
| `busy4` 或 `done4` | **100 分钟** |

---

## 5. 状态管理

### 5.1 后端状态机（socket_status.json）

```mermaid
stateDiagram-v2
    [*] --> free : 初始化 / 超时清理

    free --> busy1_sse_chat : 用户请求 sse-chat
    free --> busy2_sse_chat_v2 : 用户请求 sse-chat-v2
    free --> busy3_generate_time_sequence : 生成时间序列
    free --> busy4_generate_video : 生成视频

    busy1_sse_chat --> done1_sse_chat__X : 完成/异常/断开
    busy2_sse_chat_v2 --> done2_sse_chat_v2__X : 完成/异常/断开
    busy3_generate_time_sequence --> done3_generate_time_sequence__X : 完成/异常
    busy4_generate_video --> done4_generate_video__X : 完成/异常/断开

    done1_sse_chat__X --> free : up_status.py 超时 15min
    done2_sse_chat_v2__X --> free : up_status.py 超时 15min
    done3_generate_time_sequence__X --> free : up_status.py 超时 15min
    done4_generate_video__X --> free : up_status.py 超时 100min
```

> `done` 状态的 `__X` 后缀（`__1` `__2` `__3`）区分正常完成、异常退出、finally 三种路径，超时阈值相同。

### 5.2 任务状态机（user_task.json）

```mermaid
stateDiagram-v2
    [*] --> pending : video_server 写入任务
    pending --> processing : run_video 拾取（直接写 JSON）
    processing --> uploading : cut_video_main() 完成
    uploading --> completed : ossutil 上传成功，写入 oss_path
    completed --> [*]

    processing --> failed : FFmpeg CalledProcessError
    uploading --> failed : 上传异常（当前代码未显式处理）
```

> `run_video.py` 全程通过 `update_task_status()` 直接读写 `user_task.json`（含 fcntl 锁），不经过 `video_server.py` API。

---

## 6. API 端点

### 6.1 主服务器 server.py（端口 5000 / Linux:80）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/get_backend_url` | POST | 按优先级分配 SSE 后端 URL |
| `/api/get_video_id_list` | POST | 获取可用视频列表 |
| `/upload_srt` | POST | 接收并保存 SRT 到 static/download/srt |
| `/upload_video_srt` | POST | 执行机上传 SRT（需 upload_token） |
| `/download/<file_name>` | GET | 下载文件 |
| `/get_play_list` | POST | 获取播放列表 |
| `/submit_content` | POST | 提交弹幕/标签 |
| `/get_content` | POST | 获取弹幕/标签 |
| `/health_check` | GET | 健康检查 → `{"status":"healthy"}` |

### 6.2 SSE 后端 sse_server.py（端口 5001-5016）

所有端点路径前缀：`/{backend_id}-{backend_name}/`

| 端点（相对路径）| 方法 | 说明 |
|----------------|------|------|
| `sse-chat` | GET | 阶段1：SSE 流式文案生成 |
| `sse-chat-v2` | GET | 阶段2：SSE 流式脚本优化 |
| `api/generate_time_sequence` | POST | 阶段3：字幕匹配，返回 keep_intervals |
| `sse-generate-video` | GET | 阶段4：SSE 视频生成进度流 |
| `/health_check` | GET | 健康检查（无路径前缀）|

### 6.3 执行机 video_server.py（端口 8868）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/make_video` | POST | 创建/更新视频任务，写入 user_task.json |
| `/get_task` | POST | 查询任务状态（SSE 轮询用）|
| `/tasks` | GET | 全部任务列表（调试用）|
| `/health` | GET | 健康检查 → `{"code":200}` |

---

## 7. 配置文件格式

### 7.1 config.yaml（API 密钥）

```yaml
DEEPSEEK_API_KEY: sk-xxxx
BAILIAN_API_KEY:  sk-xxxx
```

### 7.2 config.json（用户与后端配置）

```json
{
  "token_list": ["user_token_1", "user_token_2"],
  "name_dic": {
    "001": "backend1",
    "002": "backend2"
  }
}
```

> `name_dic` 的值必须是纯后端名称（如 `"backend1"`），`server.py` 用 `name.split('backend')[1]` 计算端口偏移，不能包含 UUID 前缀。

### 7.3 socket_status.json（后端状态，主服务器）

```json
{
  "001": {
    "status": "free",
    "user_id": "002",
    "cur_time": 1741478400.0,
    "update_time": "2026-03-09 10:00:00"
  },
  "002": {
    "status": "busy1_sse_chat",
    "user_id": "003",
    "cur_time": 1741478500.0,
    "update_time": "2026-03-09 10:01:40"
  }
}
```

### 7.4 user_task.json（任务队列，执行机）

```json
[
  {
    "video_id": "C1872",
    "user_id": "003",
    "keep_intervals": [
      [["00:01:00,000", "00:02:30,500"], "因为在上市公司我 我做事做得很好"],
      [["00:03:10,200", "00:04:05,800"], "就是错把平台的能力当自己的能力"]
    ],
    "created_at": "2026-03-09 10:00:00",
    "status": "completed",
    "oss_path": "http://video.kaixin.wiki/hanbing/.../C1872_003_2026_03_09_10_30_00.mp4"
  }
]
```

> `keep_intervals` 每项格式为 `[[start_str, end_str], text]`，时间为 SRT 时间字符串。`step3.ffmpeg_cut_mp4()` 内部调用 `time_str_to_seconds()` 转换为浮点秒数后处理。

### 7.5 视频元数据（每个视频目录下的 .json）

```json
{
  "name": "视频显示名称"
}
```

> `config.py` 的 `get_file_info()` 读取此文件获取 `name` 字段，用于视频列表展示。

---

## 8. 部署说明

### 8.1 主服务器启动顺序

```bash
# 1. 主 API 服务（Windows:5000 / Linux:80）
python server.py

# 2. SSE 后端实例（参数：端口 名称 UUID 编号）
python sse_server.py 5001 backend1 c0929290-6d79-40de-af54-e8aae8072060 001
python sse_server.py 5002 backend2 <uuid2> 002
# ... 最多 16 个实例

# 3. 状态清理（每 30 秒）
python up_status.py

# 4. 进程监控（依赖 systemd 重启，pkill 后自动拉起）
python manager.py
```

### 8.2 执行机启动顺序

```bash
# 1. 任务管理 API
python video_server.py   # 端口 8868

# 2. 视频处理工作线程（可启动多个并发）
python run_video.py &
python run_video.py &
```

### 8.3 生产环境（Linux systemd）

```ini
# /etc/systemd/system/backend1.service
[Unit]
Description=SSE Backend 1
After=network.target

[Service]
User=root
WorkingDirectory=/root/split_video
ExecStart=/usr/bin/python3 sse_server.py 5001 backend1 c0929290-6d79-40de-af54-e8aae8072060 001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 常用运维命令
systemctl status backend1
systemctl restart backend1
journalctl -u backend1 -f

# 批量生成 systemd 配置
python run_sse_code.py
```

### 8.4 执行机 IP 配置

```python
# sse_server.py 第18行
servers = ["113.249.107.180", "113.249.107.182"]
```

`sse_generate_video()` 遍历 `servers` 列表，选取第一个成功响应的执行机执行视频任务。

---

## 9. 故障排查

### 9.1 常见问题

| 现象 | 检查点 |
|------|--------|
| SSE 连接立即断开 | Nginx 配置 `X-Accel-Buffering: no` |
| 后端全部 busy | 查看 `socket_status.json`；`up_status.py` 是否运行 |
| 视频生成无进度 | 执行机 `run_video.py` 是否运行；`user_task.json` 中 status |
| AI 匹配返回空结果 | `config.yaml` 中 API Key 是否有效；查看 backend 日志 |
| keep_intervals 全为 null | `probability < 0.88` 且降级也失败；检查 SRT 文件与文案是否匹配 |
| 视频上传失败 | 执行机上 ossutil 是否配置；查看 `user_task.json` status=uploading 是否卡住 |
| manager.py 重启后服务未起 | 确认 systemd 中配置了 `Restart=always`；Windows 环境 manager 无法重启进程 |

### 9.2 日志位置

| 服务 | 日志路径 |
|------|----------|
| server.py | `logs/app/log.txt` |
| sse_server backend1 | `logs/backend1/backend1.txt` |
| systemd 服务 | `journalctl -u backend1 -f` |
| 执行机 | 控制台 stdout（可重定向到文件）|

### 9.3 状态手动重置

```bash
# 手动将某个后端重置为 free（修改 socket_status.json）
# 将 "001" 的 status 改为 "free"
# up_status.py 会在 15/100 分钟后自动清理，也可手动编辑
```

---

*文档基于代码交叉验证生成，已修正原文档10处错误。如需更新，请以代码为准重新生成。*
