# sp_mini

当前目录只保留了“单视频压缩到约 5 分钟”所需的最小运行集。

## 目标

处理 `data/video/` 下的单视频素材。

要求：

1. 每个视频对应同名 `.mp4` 和 `.srt`
2. 尽量压缩到约 5 分钟
3. 优先删除废话、口头禅、重复表达、无信息增量内容
4. 尽量保留观点、结论、关键解释、转折、冲突、案例、方法、结果
5. 必须尽量保持原时间顺序和叙事顺序

## 当前保留的核心文件

- `main.py`
- `settings.py`
- `scripts/run_single_video_5min_batch.py`
- `make_time/`
- `make_video/`
- `batch/logger.py`
- `data/config/config.yaml`
- `docs/core/session_context_2026_04_14.md`

## 运行方式

在目录 `C:\codex\sp_v1\split_video\mini\sp_mini` 下执行：

```bash
python scripts/run_single_video_5min_batch.py
```

可选参数：

```bash
python scripts/run_single_video_5min_batch.py --video_dir data/video --output_dir data/output_5min --log_root data/run_logs/single_video_5min
```

## 输入输出

- 输入字幕目录：`data/video`
- 输入视频目录：`data/video`
- 默认输出目录：`data/output_5min`
- 默认日志目录：`data/run_logs/single_video_5min/<run_id>/`

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
- `*_5min.mp4`

## 说明

1. 当前目录不依赖 `sp_video` 目录。
2. 当前项目已经清理掉测试、实验、多视频和无关文档，只保留本轮任务所需代码。
3. 如果重新运行前要清理旧结果，优先删除 `data/output_5min` 和对应日志目录，不要删除 `data/video` 与 `data/config/config.yaml`。
