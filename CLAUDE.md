# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

智能视频分割 - 基于 Flask 的 Web 服务，使用 AI 分析视频字幕，根据用户提供的脚本来生成编辑后的视频片段。

## 部署架构

### 主服务器 (Main Server)
- `server.py` (端口 80/443) - API 网关：文件上传下载、后端路由分发、用户认证
- `sse_server.py` (端口 5001-5016) - SSE 后端：AI 聊天、时间序列生成、视频生成请求（16 个实例）
- `manager.py` - 进程健康监控，自动重启失败服务（pkill + 重启）
- `up_status.py` - 清理超时的后端状态任务

### 执行机 (Worker Machine)
- `video_server.py` (端口 8868) - 视频任务管理服务器
- `run_video.py` - 视频处理工作线程：轮询 `user_task.json` 并执行 ffmpeg 操作

```
客户端 → server.py → sse_server(端口 5001-5016) → video_server(执行机 8868) → run_video → ffmpeg → OSS
```

## 运行命令

```bash
# 主服务器
python server.py

# SSE 后端实例（参数：端口 后端名称 后端ID 后端编号）
python sse_server.py 5001 backend1 c0929290-6d79-40de-af54-e8aae8072060 001

# 执行机
python video_server.py
python run_video.py

# 生成多后端实例代码（部署用）
python run_sse_code.py
```

## 配置文件

| 文件 | 说明 |
|------|------|
| `./data/config/config.yaml` | API 密钥 (DEEPSEEK_API_KEY, BAILIAN_API_KEY) |
| `./data/config/config.json` | token_list（用户令牌）、name_dic（后端名称映射）|
| `./data/config/socket_status.json` | 后端状态跟踪（并发访问，Linux 用 fcntl 加锁）|
| `./data/hanbing/` | 视频数据：每个视频目录含 `.srt`、`.mp4`、`.json`（含 `name` 字段）|
| `user_task.json` | 视频任务队列（执行机，video_server 写入，run_video 轮询读取）|
| `video_list.json` | 已处理视频 ID 列表（run_video 维护，防止重复处理）|
| `keep_intervals.json` | 每次 AI 匹配后写出的调试文件 |

## 核心工作流程

### 1. 后端分配 (`server.py:get_backend_url`)
按优先级从 `socket_status.json` 选取后端：
1. 该用户 done 状态的后端（专属复用）
2. free 状态的后端
3. done 超过 180 秒且最久的后端（抢占）

### 2. SSE 后端 URL 结构
每个 sse_server 实例的路由包含 `backend_id` 和 `backend_name`：
```
/{backend_id}-{backend_name}/sse-chat
/{backend_id}-{backend_name}/sse-chat-v2
/{backend_id}-{backend_name}/api/generate_time_sequence
/{backend_id}-{backend_name}/sse-generate-video
```
`backend_id` 是 UUID，通过命令行参数传入，固定嵌入每个实例的路由。

### 3. 时间序列生成 (`make_time/`)
入口：`step2.get_keep_intervals(srt_path, script)` → `mode2.get_intervals_by_mode2()`

**脚本格式解析** (`mode2.get_yuanwen_mode2`)：
- 支持带时间的段落标题：`观点：xxx（00:02:15-00:05:15）`
- 支持无时间的段落标签：`观点：`、`解释：`、`故事：`、`出路：`（`glo_part_list`）
- 每段下方是 SRT 格式的时间轴行 + 文本行

**AI 匹配两阶段验证** (`util.get_unit_interval_by_ai`)：
1. 第一次 AI 调用：给定原文句子和候选字幕，返回 `{id_list, text}`
2. 第二次 AI 调用：验证匹配相似度，返回 `{probability}`
3. 阈值 `glo_check_probability = 0.88`；连续 id_list 额外加 0.05 概率奖励
4. 未通过阈值则调用 `get_intervals_by_ai_find()` 做全文搜索兜底

**合并逻辑** (`util.merge_intervals`)：相邻字幕 id 连续时自动合并为一个片段。

### 4. 视频生成流程 (`run_video.py`)
```
轮询 user_task.json (status=pending)
  → extract_audio (提取 WAV，跳过已存在)
  → cut_and_merge_video_img (无损切割：-c:v copy -c:a copy)
  → merge 音视频（ffmpeg -c:v copy -c:a aac）
  → ossutil 上传 → 更新 status=completed + oss_path
```

## 关键模式

- **SRT token 分割**：SRT 超过 `limit_prompt=8192` tokens 时，`split_srt_content()` 按段落分割，返回 `(parts, split_time)`（分割点的时间戳）
- **文件锁**：Linux 用 `fcntl.flock()`；Windows 跳过（通过 `is_windows()` 判断）
- **AI 模型路由** (`chat.py:ask_ai`)：支持 `deepseek`（直连 api.deepseek.com）、`deepseek-r1`、`deepseek-r1-70b`（均通过阿里云 dashscope）
- **`...` / `……` 分割**：脚本中的省略号表示该句需拆成两段分别匹配
- **视频文件 lookup**：`config._data_cache` 缓存 `video_id → [srt_path, mp4_path, name]`；每个视频目录下的 `.json` 文件提供 `name` 字段

## 健康检查端点

- `GET /health_check` → `{"status": "healthy"}` (server.py, sse_server.py)
- `GET /health` → `{"code": 200, ...}` (video_server.py)

## 日志

- `logs/app/log.txt` - 主服务器
- `logs/backendN/backendN.txt` - 各 SSE 后端
