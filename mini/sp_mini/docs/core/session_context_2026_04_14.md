# Session Context 2026-04-14

## 固定工作目录

当前工作目录固定为：

`C:\codex\sp_v1\split_video\mini\sp_mini`

非常重要：

1. 所有操作都只能在这个目录及其内部进行。
2. 不允许读或依赖 `C:\codex\sp_v1\split_video\mini\sp_video` 的代码或文档。
3. 如果发现历史路径、旧配置、旧文档提到 `sp_video`，也只能参考当前 `sp_mini` 目录内已有代码，不能跳到别的目录取代码。

## 当前任务背景

1. 当前任务只处理 10 个彼此独立的单视频，不做多视频拼接。
2. 输入目录固定为：
   `C:\codex\sp_v1\split_video\mini\sp_mini\data\video`
3. 每个视频都应有同名 `.mp4` 和 `.srt`。
4. 输出目标是把每个视频压缩到约 5 分钟。
5. 核心要求：
   - 删除废话、口头禅、重复表达、无信息增量内容
   - 尽量保留观点、结论、关键解释、转折、冲突、案例、方法、结果
   - 必须尽量保持原时间顺序和叙事顺序
   - 原则上不允许把后面的内容搬到前面
6. 这是一次临时、快速、实用优先的任务，不做大工程。

## 本轮确认后的问题与结论

1. 之前跑出的 `data/output_5min` 结果整体偏短，很多视频只保留到 1 到 2 分钟，不符合“约 5 分钟顺序压缩版”的目标。
2. 主要原因不是 ffmpeg，而是前两阶段提示词仍然过度偏向“金句摘录”和“高冲击句筛选”。
3. 旧批处理脚本缺少按次归档日志；只保留了中间文件和控制台输出，不利于 2 小时以上的长跑复盘。

## 已完成的代码改动

1. 修改了 [main.py](/C:/codex/sp_v1/split_video/mini/sp_mini/main.py)
   - `PHASE1_PROMPT` 从“短视频素材筛选员”调整为更偏“顺序压缩编辑”
   - 不再强调“宁可精不要贪多”，而是强调保留足够素材，让下一阶段能做出约 4 到 6 分钟成片
   - 明确不能只挑最炸的句子，要优先保留叙事主线、关键解释和完整表达单元
   - `PHASE2_PROMPT` 明确目标是“顺序压缩版脚本”，不是 1 到 2 分钟金句拼贴
   - 增加“尽量避免少于 2 秒的碎片、残句、脱离上下文难懂的片段”

2. 修改了 [scripts/run_single_video_5min_batch.py](/C:/codex/sp_v1/split_video/mini/sp_mini/scripts/run_single_video_5min_batch.py)
   - 每次运行都会在 `data/run_logs/single_video_5min/<run_id>/` 下生成独立日志目录
   - 新增：
     - `run.log`
     - `events.jsonl`
     - `prompt_snapshot.json`
     - `run_summary.json`
   - 每个视频的 `summary.json` 现在会记录：
     - `original_duration_sec`
     - `selected_duration_sec`
     - `compression_ratio`
     - `duration_status`
     - `step1_count`
     - `step2_count`
   - 批处理阶段会记录视频开始、阶段耗时、匹配数量、最终时长是否过短等结构化事件

3. 做了目录大清理
   - 删除了测试、实验、多视频、视觉评分、无关文档和旧缓存
   - 当前目录只保留单视频 5 分钟任务所需最小运行集

## 当前保留的最小运行集

1. 根目录：
   - `main.py`
   - `settings.py`
   - `README.md`
2. 脚本：
   - `scripts/run_single_video_5min_batch.py`
3. 代码目录：
   - `make_time/`
   - `make_video/`
   - `batch/logger.py`
   - `batch/__init__.py`
4. 数据目录：
   - `data/config/config.yaml`
   - `data/video/`
5. 文档：
   - `docs/core/session_context_2026_04_14.md`

## 运行方式

运行目录必须是：

`C:\codex\sp_v1\split_video\mini\sp_mini`

运行命令：

```bash
python scripts/run_single_video_5min_batch.py
```

如果要显式指定日志根目录：

```bash
python scripts/run_single_video_5min_batch.py --log_root data/run_logs/single_video_5min
```

默认路径：

1. 输入目录：`data/video`
2. 输出目录：`data/output_5min`
3. 日志目录：`data/run_logs/single_video_5min/<run_id>/`

## 后续协作注意事项

1. 现在的项目已经不是原来的完整仓库形态，而是“面向当前任务的最小运行集”。
2. 后续如果再做删除，必须先确认是否在当前调用链上，否则容易删坏运行。
3. 后续如果要复盘长跑结果，优先读取该次运行的：
   - `run_summary.json`
   - `events.jsonl`
   - `prompt_snapshot.json`
4. 不依赖 `sp_video` 目录。
