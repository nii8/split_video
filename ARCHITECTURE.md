# 智能视频分割系统 - 完整技术架构文档

## 1. 工程概述

### 1.1 项目简介

智能视频分割系统是一个基于 Flask 的 Web 服务平台，通过 AI 大模型分析视频字幕内容，根据用户提供的脚本/文案自动生成精确剪辑的视频片段。系统采用**主从架构**，支持多执行机并行处理请求。

### 1.2 系统角色划分

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           主服务器 (Master)                              │
│  运行组件：server.py, sse_server.py, manager.py                          │
│  职责：API 网关、用户请求接收、AI 对话、状态管理、任务分发                │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTP 请求
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         执行机 (Worker) × N                              │
│  运行组件：video_server.py, run_video.py                                 │
│  职责：视频任务队列管理、FFmpeg 视频剪辑、OSS 上传                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 技术栈

| 层次 | 技术组件 |
|------|----------|
| Web 框架 | Flask + Flask-CORS |
| AI 模型 | DeepSeek API / 通义千问 (Bailian) |
| 视频处理 | FFmpeg / FFprobe |
| 实时通信 | SSE (Server-Sent Events) |
| 任务队列 | JSON 文件 + 轮询机制 |
| 日志系统 | Python logging (按天滚动) |
| 部署方式 | systemd 服务 (Linux) / 直接运行 (Windows) |
| 对象存储 | OSS (阿里云，仅 Linux) |

---

## 2. 系统架构总览

### 2.1 物理架构图

```mermaid
graph TB
    subgraph Client["客户端 (前端)"]
        C1[Web 浏览器]
    end
    
    subgraph Master["主服务器集群"]
        S1[server.py:5000<br/>API 网关]
        S2[sse_server.py:5001-5016<br/>SSE 后端 ×16]
        S3[manager.py<br/>进程监控]
        S4[数据共享区<br/>socket_status.json]
    end
    
    subgraph Worker["执行机集群 ×N"]
        W1[video_server.py:8868<br/>任务管理]
        W2[run_video.py<br/>视频处理]
        W3[user_task.json<br/>任务队列]
    end
    
    subgraph External["外部服务"]
        A1[DeepSeek API]
        A2[Bailian API]
        O1[OSS 对象存储]
    end
    
    subgraph Storage["存储层"]
        D1[SRT 字幕文件]
        D2[MP4 视频文件]
        D3[HLS 分片]
    end
    
    C1 -->|HTTP| S1
    C1 -->|SSE| S2
    S3 -->|健康检查 | S1
    S3 -->|健康检查 | S2
    S2 <-->|读写 | S4
    S2 <-->|HTTP | W1
    W1 <-->|读写 | W3
    W2 -->|轮询 | W3
    W2 -->|直接修改 | W3
    W2 -->|FFmpeg| D2
    W2 -->|上传 | O1
    W2 -->|同步 SRT| M1
    S2 -->|AI 调用 | A1
    S2 -->|AI 调用 | A2
    S1 -->|静态文件 | D3
```

### 2.2 主服务器与执行机边界

```mermaid
graph LR
    subgraph Master["主服务器 (Master Server)"]
        M1[server.py<br/>端口：5000/80<br/>职责：API 网关]
        M2[sse_server.py<br/>端口：5001-5016<br/>职责：AI 处理]
        M3[manager.py<br/>职责：进程监控]
        M4[共享状态<br/>socket_status.json]
    end
    
    subgraph Worker["执行机 (Worker Machine)"]
        W1[video_server.py<br/>端口：8868<br/>职责：任务管理]
        W2[run_video.py<br/>职责：视频剪辑]
        W3[任务队列<br/>user_task.json]
        W4[视频资源<br/>MP4/SRT]
    end
    
    M2 -->|1.make_video 请求 | W1
    M2 -->|2.轮询 get_task| W1
    W2 -->|3.轮询任务 | W3
    W2 -->|4.上传 SRT| M1
    W2 -->|5.上传视频 | OSS[OSS 存储]
    
    style Master fill:#e1f5ff
    style Worker fill:#fff4e1
```

**关键界限说明：**

| 职责 | 主服务器 | 执行机 |
|------|---------|-------|
| 用户认证 | ✅ | ❌ |
| AI 对话 (SSE) | ✅ | ❌ |
| 文案 - 字幕匹配 | ✅ | ❌ |
| 任务队列管理 | ❌ | ✅ |
| FFmpeg 视频剪辑 | ❌ | ✅ |
| OSS 上传 | ❌ | ✅ |
| 进程监控 | ✅ | ❌ |
| SRT 同步 | 接收端 | 发送端 (提取帧时) |

### 2.3 关键数据流向说明

```
┌─────────────────────────────────────────────────────────────────────────┐
│  重要澄清：视频生成请求的发起者                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  ❌ 错误理解：server.py → video_server.py                               │
│  ✅ 正确理解：sse_server.py → video_server.py                           │
│                                                                         │
│  原因：sse_server.py 中的 sse_generate_video() 函数直接 HTTP 调用       │
│  执行机的 /make_video 端点，并持续轮询 /get_task 获取进度               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  重要澄清：任务状态更新方式                                             │
├─────────────────────────────────────────────────────────────────────────┤
│  ❌ 错误理解：run_video.py 调用 video_server.py API 更新状态            │
│  ✅ 正确理解：run_video.py 直接修改 user_task.json 文件                 │
│                                                                         │
│  原因：run_video.py 的 update_task_status() 函数直接读写 JSON 文件，    │
│  使用 fcntl 文件锁保证并发安全，不调用 video_server.py 的任何 API        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  重要澄清：SRT 文件同步时机                                             │
├─────────────────────────────────────────────────────────────────────────┤
│  执行机在 get_video_imgs() 提取视频帧时，调用 send_srt() 将 SRT 上传   │
│  到主服务器的 /upload_video_srt 端点，确保主服务器有最新的 SRT 文件    │
│  用于后续 AI 文案匹配                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 数据流动图

### 3.1 完整业务流程

```mermaid
sequenceDiagram
    participant User as 用户前端
    participant Server as server.py<br/>(主服务器)
    participant SSE as sse_server.py<br/>(主服务器)
    participant VideoS as video_server.py<br/>(执行机)
    participant RunV as run_video.py<br/>(执行机)
    participant OSS as OSS 存储
    
    Note over User,SSE: 阶段 1: AI 对话生成文案
    User->>Server: 1.获取后端 URL
    Server-->>User: 返回空闲 backend 地址
    User->>SSE: 2.SSE 连接 (prompt)
    SSE->>SSE: 加载 SRT 字幕
    SSE->>DeepSeek: 3.AI 流式生成
    DeepSeek-->>SSE: 流式返回文案
    SSE-->>User: SSE 推送文案片段
    
    Note over User,SSE: 阶段 2: 脚本优化
    User->>SSE: 4.SSE v2 (优化脚本)
    SSE->>DeepSeek: AI 优化
    DeepSeek-->>SSE: 返回优化脚本
    SSE-->>User: SSE 推送优化结果
    
    Note over User,SSE: 阶段 3: 时间序列生成
    User->>SSE: 5.POST 保存脚本
    SSE->>SSE: 文案 - 字幕匹配
    SSE-->>User: 返回 keep_intervals
    
    Note over User,VideoS: 阶段 4: 视频生成
    User->>SSE: 6.SSE 生成视频请求
    SSE->>VideoS: 7.POST /make_video
    VideoS->>VideoS: 写入 user_task.json
    VideoS-->>SSE: 返回 task_id
    SSE-->>User: 推送任务已启动
    
    Note over RunV,VideoS: 阶段 5: 视频处理 (执行机异步)
    RunV->>RunV: 轮询 user_task.json
    RunV->>RunV: 发现 pending 任务
    RunV->>Server: 同步 SRT 文件 (提取帧时)
    RunV->>RunV: FFmpeg 剪辑视频
    RunV->>RunV: 上传 OSS
    RunV->>RunV: 直接更新 user_task.json
    
    Note over User,SSE: 阶段 6: 进度轮询
    User->>SSE: SSE 持续连接
    SSE->>VideoS: 轮询 /get_task
    VideoS-->>SSE: 返回任务状态
    SSE-->>User: 推送进度更新
    SSE-->>User: 推送 oss_path
```

### 3.2 主服务器内部数据流

```mermaid
graph TD
    subgraph API_Layer
        A1[upload_srt]
        A2[get_backend_url]
        A3[get_content]
        A4[upload_video_srt]
    end
    
    subgraph SSE_Layer
        S1[sse-chat]
        S2[sse-chat-v2]
        S3[api/generate_time_sequence]
        S4[sse-generate-video]
    end
    
    subgraph AI_Module
        M1[make_time.step2]
        M2[make_time.mode2]
        M3[make_time.chat]
    end
    
    subgraph State_Mgr
        ST1[socket_status.json]
    end
    
    A2 --> S1
    S1 --> M1
    S2 --> M1
    S3 --> M1
    M1 --> M2
    M2 --> M3
    S4 --> A4
    S1 <--> ST1
    S2 <--> ST1
    S3 <--> ST1
    S4 <--> ST1
```

### 3.3 执行机内部数据流

```mermaid
graph TD
    subgraph TaskAPI
        T1[make_video]
        T2[get_task]
        T3[tasks]
    end
    
    subgraph Worker
        W1[轮询循环]
        W2[get_first_pending_task]
        W3[cut_video_main]
        W4[upload_video]
        W5[get_video_imgs]
        W6[send_srt]
    end
    
    subgraph VideoProc
        V1[extract_audio]
        V2[cut_and_merge_audio]
        V3[cut_and_merge_video_img]
        V4[ffmpeg 合成]
    end
    
    subgraph Queue
        Q1[user_task.json]
    end
    
    subgraph External
        Server1[server.py]
        OSS1[OSS 对象存储]
    end
    
    T1 --> Q1
    T2 --> Q1
    W1 --> W2
    W2 --> Q1
    W2 --> W3
    W2 --> W5
    W5 --> W6
    W6 --> Server1
    W3 --> V1
    V1 --> V2
    V2 --> V3
    V3 --> V4
    W3 --> W4
    W4 --> OSS1
    W4 -.-> Q1
```

---

## 4. 核心模块详解

### 4.1 模块依赖关系图

```mermaid
graph TB
    subgraph Server["主服务器模块"]
        server[server.py<br/>主 API 服务器]
        sse[sse_server.py<br/>SSE 后端]
        manager[manager.py<br/>进程监控]
    end
    
    subgraph Worker["执行机模块"]
        videoserver[video_server.py<br/>任务管理]
        runvideo[run_video.py<br/>视频处理]
    end
    
    subgraph MakeTime["make_time 模块"]
        step2[step2.py<br/>入口函数]
        mode2[mode2.py<br/>文案匹配核心]
        util[util.py<br/>AI 工具函数]
        chat[chat.py<br/>AI 客户端]
    end
    
    subgraph MakeVideo["make_video 模块"]
        step3[step3.py<br/>视频剪辑核心]
    end
    
    subgraph Common["公共模块"]
        config[config.py<br/>配置管理]
        mylog[mylog.py<br/>日志工具]
    end
    
    server --> config
    server --> mylog
    sse --> config
    sse --> step2
    videoserver --> config
    runvideo --> step3
    runvideo --> config
    step2 --> mode2
    mode2 --> util
    util --> chat
    step3 --> config
    manager -.健康检查.-> server
    manager -.健康检查.-> sse
```

### 4.2 AI 字幕匹配流程

```mermaid
flowchart TD
    Start[开始] --> Parse[解析用户文案<br/>get_yuanwen_mode2]
    Parse --> Extract[提取 SRT 字幕<br/>parse_zimu_content]
    Extract --> Split[分割文案段落<br/>按标题/时间轴]
    
    subgraph AI_Match["AI 匹配循环"]
        Split --> Loop{遍历段落}
        Loop --> GenPrompt[生成 AI 提示词<br/>get_id_list_promot_mode2]
        GenPrompt --> CallAI[调用 AI 模型<br/>ask_ai]
        CallAI --> ParseJSON[解析 JSON 输出<br/>get_ai_json]
        ParseJSON --> CheckSim[相似度验证<br/>get_check_promot]
        CheckSim --> Prob{probability > 0.88?}
        Prob -->|No| Fallback[降级处理<br/>直接查找]
        Prob -->|Yes| Keep[保留时间区间]
        Fallback --> Keep
        Keep --> Loop
    end
    
    Loop --> Merge[合并连续区间<br/>merge_intervals]
    Merge --> Output[输出 keep_intervals]
```

### 4.3 视频剪辑流程

```mermaid
flowchart TD
    Start[开始 cut_video_main] --> Extract[提取音频<br/>extract_audio]
    Extract --> CutAudio[剪辑合并音频<br/>cut_and_merge_audio]
    CutAudio --> CutImg[剪辑合并画面<br/>cut_and_merge_video_img]
    CutImg --> Synthesize[音视频合成<br/>ffmpeg merge]
    Synthesize --> Upload[上传 OSS<br/>ossutil cp]
    Upload --> Done[完成]
    
    subgraph CutAudio_Detail["音频处理"]
        Extract --> FF1[ffmpeg -i mp4 -vn wav]
        FF1 --> Loop1[遍历 keep_intervals]
        Loop1 --> Cut1[ffmpeg -ss -to 切片]
        Cut1 --> Concat1[concat 拼接]
    end
    
    subgraph CutImg_Detail["画面处理"]
        CutImg --> FF2[ffmpeg 提取全部帧]
        FF2 --> Calc[计算帧范围<br/>start*fps ~ end*fps]
        Calc --> Select[选择保留帧]
        Select --> FF3[ffmpeg 从帧生成视频]
    end
```

---

## 5. 状态管理

### 5.1 后端状态流转 (socket_status.json)

```mermaid
stateDiagram-v2
    [*] --> free: 初始化
    
    state "busy 状态组" as busy {
        busy1: busy1_sse_chat<br/>5min
        busy2: busy2_sse_chat_v2<br/>5min
        busy3: busy3_generate_time_sequence<br/>3min
        busy4: busy4_generate_video<br/>15min
    }
    
    state "done 状态组" as done {
        done1: done1_sse_chat__1/2/3<br/>3min
        done2: done2_sse_chat_v2__1/2/3<br/>3min
        done3: done3_generate_time_sequence__1/2/3<br/>3min
        done4: done4_generate_video__1/2/3/4<br/>3min
    }
    
    free --> busy1: 用户请求 chat
    free --> busy2: 用户请求 chat-v2
    free --> busy3: 生成时间序列
    free --> busy4: 生成视频
    
    busy1 --> done1: 完成
    busy2 --> done2: 完成
    busy3 --> done3: 完成
    busy4 --> done4: 完成
    
    done1 --> free: 超时 (180s)
    done2 --> free: 超时 (180s)
    done3 --> free: 超时 (180s)
    done4 --> free: 超时 (180s)
```

### 5.2 任务状态流转 (user_task.json)

```mermaid
stateDiagram-v2
    [*] --> pending: 创建任务
    
    pending --> processing: run_video 拾取
    processing --> uploading: 视频剪辑完成
    uploading --> completed: OSS 上传完成
    completed --> [*]
    
    processing --> failed: FFmpeg 失败
    uploading --> failed: 上传失败
    failed --> [*]
```

---

## 6. 关键 API 端点

### 6.1 主服务器 API (server.py:5000)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/upload_srt` | POST | 上传 SRT 字幕文件 |
| `/download/<file_name>` | GET | 下载文件 |
| `/get_play_list` | POST | 获取播放列表 |
| `/submit_content` | POST | 提交弹幕/标签 |
| `/get_content` | POST | 获取弹幕/标签 |
| `/api/get_video_id_list` | POST | 获取视频 ID 列表 |
| `/upload_video_srt` | POST | 执行机上传 SRT |
| `/api/get_backend_url` | POST | 获取空闲后端地址 |

### 6.2 SSE 后端 API (sse_server.py:5001-5016)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/{id}-{name}/sse-chat` | GET | SSE 流式对话 (阶段 1) |
| `/{id}-{name}/sse-chat-v2` | GET | SSE 流式对话 (阶段 2) |
| `/{id}-{name}/api/generate_time_sequence` | POST | 保存脚本生成时间序列 |
| `/{id}-{name}/sse-generate-video` | GET | SSE 视频生成 (阶段 4) |
| `/health_check` | GET | 健康检查 |

### 6.3 视频服务器 API (video_server.py:8868)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/make_video` | POST | 创建视频任务 |
| `/get_task` | POST | 查询任务状态 |
| `/tasks` | GET | 获取任务列表 |
| `/health` | GET | 健康检查 |

---

## 7. 配置文件结构

### 7.1 socket_status.json (主服务器共享状态)

```json
{
  "001": {
    "status": "busy1_sse_chat",
    "user_id": "003",
    "cur_time": 1678888888,
    "update_time": "2026-03-08 10:00:00"
  },
  "002": {
    "status": "free",
    "user_id": null,
    "cur_time": 1678888000,
    "update_time": "2026-03-08 09:45:00"
  }
}
```

### 7.2 user_task.json (执行机任务队列)

```json
[
  {
    "video_id": "C1872",
    "user_id": "003",
    "keep_intervals": [[120.5, 135.2], [180.0, 200.5]],
    "created_at": "2026-03-08 10:00:00",
    "status": "processing",
    "oss_path": "http://video.kaixin.wiki/hanbing/.../C1872_003_..."
  }
]
```

---

## 8. 部署架构

### 8.1 主服务器部署

```bash
# server.py (API 网关)
python server.py  # Windows:5000  Linux:80

# sse_server.py (16 个实例)
python sse_server.py 5001 backend1 <backend_id> 001
python sse_server.py 5002 backend1 <backend_id> 002
...
python sse_server.py 5016 backend1 <backend_id> 016

# manager.py (进程监控)
python manager.py
```

### 8.2 执行机部署

```bash
# video_server.py (任务管理)
python video_server.py  # 端口 8868

# run_video.py (视频处理，可运行多个)
python run_video.py &
python run_video.py &
```

### 8.3 Linux systemd 配置

```ini
# /etc/systemd/system/backend1.service
[Unit]
Description=SSE Backend 1
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/root/split_video
ExecStart=/usr/bin/python3 sse_server.py 5001 backend1 c0929290-6d79-40de-af54-e8aae8072060 001
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 9. 文件目录结构

```
split_video/
├── server.py                    # 主 API 服务器
├── sse_server.py                # SSE 后端
├── video_server.py              # 视频任务服务器 (执行机)
├── run_video.py                 # 视频处理工作进程 (执行机)
├── manager.py                   # 进程监控
├── config.py                    # 配置管理
├── mylog.py                     # 日志工具
├── make_time/                   # AI 字幕匹配模块
│   ├── step2.py                 # 入口函数
│   ├── mode2.py                 # 文案匹配核心
│   ├── util.py                  # AI 工具函数
│   └── chat.py                  # AI 客户端
├── make_video/                  # 视频处理模块
│   └── step3.py                 # 视频剪辑核心
├── data/                        # 数据目录
│   ├── hanbing/                 # 视频数据
│   │   ├── *.srt                # 字幕文件
│   │   ├── *.mp4                # 视频文件
│   │   └── *.json               # 元数据
│   └── config/                  # 配置文件
│       ├── socket_status.json   # 后端状态
│       └── config.yaml          # API 密钥
├── logs/                        # 日志目录
│   ├── app/                     # 主服务器日志
│   └── backend1/                # SSE 后端日志
└── video/                       # 视频输出
    ├── hls/                     # HLS 分片
    └── src/                     # 原始视频
```

---

## 10. 关键代码逻辑

### 10.1 后端分配逻辑 (server.py:get_backend_url)

```
1. 优先分配用户之前使用的 done 状态后端
2. 其次分配用户之前使用的 free 状态后端
3. 再次分配任意 free 状态后端
4. 最后分配 done 状态超时 (>180s) 的后端
```

### 10.2 文案 - 字幕匹配算法 (mode2.py)

```
1. 解析用户文案为结构化段落 (标题 + 时间轴 + 字幕)
2. 对每个字幕条目，生成 AI 提示词
3. AI 返回匹配的字幕 id_list
4. 调用 AI 验证相似度 (probability > 0.88)
5. 合并连续区间，输出 keep_intervals
```

### 10.3 视频剪辑算法 (step3.py)

```
1. 提取 MP4 音频为 WAV
2. 根据 keep_intervals 切割音频片段
3. 使用 ffmpeg concat 拼接音频
4. 提取视频全部帧 (30fps)
5. 根据 keep_intervals 选择保留帧
6. 从帧重新生成视频
7. 合并视频和音频
8. 上传 OSS
```

---

## 11. 安全与并发

### 11.1 文件锁机制

```python
# Linux 非阻塞文件锁
if not is_windows():
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # 写锁
    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # 读锁
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # 释放
```

### 11.2 安全验证

- `upload_token` 验证执行机上传请求
- 用户 `token` 验证前端请求
- 所有用户输入在文件操作前验证

---

## 12. 故障排查

### 12.1 常见问题

| 问题 | 检查点 |
|------|--------|
| SSE 连接中断 | 检查 Nginx `X-Accel-Buffering` 配置 |
| 视频生成超时 | 检查 `run_video.py` 进程状态 |
| 后端全忙 | 检查 `socket_status.json` 状态分布 |
| AI 调用失败 | 检查 API Key 和网络连接 |

### 12.2 日志位置

- 主服务器：`logs/app/log.txt`
- SSE 后端：`logs/backend1/*.txt`
- 系统日志：`journalctl -u backend1 -f`
