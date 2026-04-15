# sp_mini

`sp_mini` 是当前任务的最小运行集，只负责单视频压缩，不依赖 `sp_video`。

当前同时保留两套版本：

1. 短精华版
2. 5 分钟顺序压缩版

## 目标

处理 `data/video/` 下的单视频素材。

基本要求：

1. 每个视频对应同名 `.mp4` 和 `.srt`
2. 优先删除废话、口头禅、重复表达、无信息增量内容
3. 尽量保留观点、结论、关键解释、转折、冲突、案例、方法、结果
4. 尽量保持原始时间顺序和叙事顺序

## 双版本说明

### 短精华版

- 脚本：`scripts/run_single_video_short_batch.py`
- 目标：约 1 到 2 分钟高密度短精华
- 输出目录：`data/output_short`
- 日志目录：`data/run_logs/single_video_short/<run_id>/`
- 输出视频名：`*_short.mp4`
- prompt 位置：脚本内部

### 5 分钟版

- 脚本：`scripts/run_single_video_5min_batch.py`
- 目标：约 4 到 6 分钟顺序压缩版
- 输出目录：`data/output_5min`
- 日志目录：`data/run_logs/single_video_5min/<run_id>/`
- 输出视频名：`*_5min.mp4`
- prompt 位置：`main.py`

补充：

1. 5 分钟版如果首轮结果明显过短，会触发一次更保守的扩充重试。
2. 重试产物会额外落盘，便于复盘。

## 运行方式

在目录 `C:\codex\sp_v1\split_video\mini\sp_mini` 下执行。

短精华版：

```bash
python scripts/run_single_video_short_batch.py
```

5 分钟版：

```bash
python scripts/run_single_video_5min_batch.py
```

可选参数示例：

```bash
python scripts/run_single_video_short_batch.py --video_dir data/video --output_dir data/output_short --log_root data/run_logs/single_video_short
python scripts/run_single_video_5min_batch.py --video_dir data/video --output_dir data/output_5min --log_root data/run_logs/single_video_5min
```

## 输入输出

- 输入字幕目录：`data/video`
- 输入视频目录：`data/video`
- 短版默认输出目录：`data/output_short`
- 5 分钟版默认输出目录：`data/output_5min`

每次运行会生成：

- `run.log`
- `events.jsonl`
- `prompt_snapshot.json`
- `run_summary.json`

每个视频目录会生成：

- `step1.txt`
- `step2.txt`
- `intervals.json`
- `summary.json`
- 对应输出视频

如果 5 分钟版触发扩充重试，还会额外生成：

- `step2_retry1.txt`
- `intervals_retry1.json`

## 打印与日志

当前输出分三层：

### 终端打印

给人实时看进度，格式统一为：

```text
2026/04/15 07:28:20 [INFO] ...
```

### 结构化日志

写入 `events.jsonl`，给事后复盘和统计用。

### Debug 输出

由 `settings.py` 中的 `OUTPUT_DEBUG_ENABLED` 控制。

```python
OUTPUT_DEBUG_ENABLED = False
```

含义：

1. `False`：默认关闭详细调试输出
2. `True`：打开匹配细节、解析细节等调试信息

这个开关只影响 `DEBUG` 级打印，不影响：

1. 正常的 `[INFO] / [WARN] / [ERROR]`
2. `events.jsonl` 结构化日志

## 当前最重要的经验

1. 短版和 5 分钟版必须分开维护，不能共用同一套 prompt。
2. 长跑任务必须按次归档日志，不能只靠控制台输出。
3. 5 分钟版的核心问题不是 ffmpeg，而是 `step2 -> phase3` 的内容质量。
4. 格式问题和内容粒度问题要分开看，不能混为一谈。

## 相关文档

- [docs/core/session_context_2026_04_14.md](docs/core/session_context_2026_04_14.md)
- [docs/core/session_context_2026_04_15.md](docs/core/session_context_2026_04_15.md)
