# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

智能视频分割 - 基于 Flask 的 Web 服务，使用 AI 分析视频字幕，根据用户提供的脚本来生成编辑后的视频片段。

## 部署架构

### 主服务器 (Main Server)
运行以下服务：
- `server.py` (端口 80/5000/443) - API 网关：文件上传下载、后端路由分发、用户认证
- `sse_server.py` (端口 5001-5016) - SSE 后端：AI 聊天、时间序列生成、视频生成请求（16 个实例）
- `manager.py` - 进程健康监控，自动重启失败服务
- `up_status.py` - 清理超时的后端状态任务

### 执行机 (Worker Machine) - 可有多台
运行以下服务：
- `video_server.py` (端口 8868) - 视频任务管理服务器
- `run_video.py` - 视频处理工作线程：轮询任务并执行 ffmpeg 操作

### 架构流程图

```
客户端 → server.py(主服务器) → sse_server(端口 5001-5016)
                                    ↓
                              video_server(执行机 8868)
                                    ↓
                              run_video(执行机轮询)
                                    ↓
                              ffmpeg 处理 → OSS 上传
```

## 模块结构

```
├── server.py              # 主服务器 - API 网关
├── sse_server.py          # SSE 后端模板 (16 个实例)
├── video_server.py        # 视频任务管理 (执行机)
├── run_video.py           # 视频处理工作线程 (执行机)
├── manager.py             # 进程监控 (主服务器)
├── up_status.py           # 状态清理 (主服务器)
├── config.py              # 配置管理、SRT 解析、Token 计算
├── mylog.py               # 共享日志设置
├── run_sse_code.py        # 部署脚本：生成多后端实例代码和 systemd 配置
│
├── make_time/             # AI 字幕匹配模块
│   ├── step2.py           # 入口：get_keep_intervals()
│   ├── mode2.py           # 文案解析和 AI 匹配核心逻辑
│   ├── util.py            # AI 提示词、JSON 解析、时间轴处理
│   └── chat.py            # 多模型 AI 客户端 (DeepSeek/Bailian)
│
├── make_video/            # 视频处理模块
│   └── step3.py           # ffmpeg 切割、音视频合并
│
├── token/                 # Token 分词器 (本地模型)
│   ├── deepseek_tokenizer.py
│   ├── tokenizer.json
│   └── tokenizer_config.json
│
└── templates/             # 前端模板
    └── video_text.html
```

## 配置文件

- `./data/config/config.yaml` - API 密钥 (DEEPSEEK_API_KEY, BAILIAN_API_KEY)
- `./data/config/config.json` - Token 列表、名称映射、后端 ID 配置
- `./data/config/socket_status.json` - 后端状态跟踪 (被多处并发访问)
- `./data/hanbing/` - 视频数据目录 (SRT + MP4 配对文件)
- `user_task.json` - 视频任务队列 (执行机上，video_server 和 run_video 共享)

## 核心工作流程

### 1. AI 聊天 (SSE 流式)
`sse-chat` → DeepSeek API → 流式响应

### 2. 时间序列生成
`/api/generate_time_sequence` → 解析 SRT → AI 匹配文案到字幕 → 返回 `keep_intervals`

### 3. 视频生成
`/sse-generate-video` → POST 到 `video_server:8868/make_video` → 写入 `user_task.json` → run_video 轮询执行

### 4. 视频处理流程 (run_video.py)
```
轮询 user_task.json (status=pending)
  → extract_audio (提取 WAV)
  → cut_and_merge_video_img (帧级别切割)
  → 合并音视频
  → upload_video (ossutil 上传)
  → 更新 status=completed
```

## 关键模式

- **SRT token 分割**: SRT 超过 `limit_prompt` (8192 tokens) 时自动分割为多个部分
- **文件锁机制**: Linux 上使用 `fcntl.flock()` 实现 JSON 文件并发访问控制
- **AI 模型路由**: `chat.py` 支持 DeepSeek (主要) 和 Bailian (备用)
- **后端负载均衡**: 通过 `socket_status.json` 分配请求 (专属→空闲→最久完成)
- **ffmpeg 无损切割**: 使用 `-c:v copy -c:a copy` 避免重新编码

## 运行命令

### 开发环境 (Windows)
```bash
# 主服务器
python server.py

# SSE 后端 (多个实例，参数：端口 后端名称 后端 ID 后端编号)
python sse_server.py 5001 backend1 c0929290-6d79-40de-af54-e8aae8072060 001

# 进程监控
python manager.py

# 状态清理
python up_status.py

# 执行机上运行
python video_server.py
python run_video.py
```

### 生产环境 (Linux systemd)
```bash
# 查看服务状态
systemctl status backend1
systemctl status video_server
systemctl status run_video

# 重启服务
systemctl restart backend1

# 查看日志
journalctl -u backend1 -f
```

### 部署脚本
```bash
# 生成多后端实例代码和 systemd 配置
python run_sse_code.py
```

## 健康检查端点

- `GET /health_check` - server.py, sse_server.py
- `GET /health` - video_server.py

## 日志文件

- `logs/app/log.txt` - 主服务器日志
- `logs/backendN/backendN.txt` - 各后端日志
- `/var/log/backend/*.log` - systemd 服务日志

## 与项目运行无关的文件

以下文件，不影响核心功能：

| 文件 | 说明 |
|------|------|
| `run_sse_code.py` | 仅用于部署时生成后端实例代码，运行时不需要 |
| `templates/video_text.html` | 前端页面，纯静态资源 |


## 依赖项

- Flask, Flask-CORS
- openai (SDK)
- transformers (本地 tokenizer)
- requests
- PyYAML
- ffmpeg, ffprobe (系统命令)
- ossutil (OSS 上传)
