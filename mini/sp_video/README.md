# sp_video

`sp_video` 是一个基于字幕和视频文件的智能剪辑模块。

输入是一组同名的 `.mp4` 和 `.srt` 文件，系统通过 LLM 从字幕里筛选内容、组织脚本、匹配回原始时间轴，再用 FFmpeg 裁切并拼接成新视频。

示例输入：

```text
data/video/demo.mp4
data/video/demo.srt
```

这里的 `demo` 就是 `video_id`。

## 1. 核心功能

当前 README 只说明 3 个核心生产模式：

| 模式 | 入口 | 目标 |
| --- | --- | --- |
| 短视频精华模式 | `scripts/run_short.py` | 每个视频生成 1 条 60 到 150 秒短视频 |
| 5 分钟顺序压缩模式 | `scripts/run_5min.py` | 每个视频生成 1 条 4 到 6 分钟版本 |
| 单视频批量候选模式 | `batch_generator.py` | 每个源视频生成多条候选，评分后输出多个结果 |

## 2. 环境准备

进入项目目录：

```bash
cd /will/split_video/mini/sp_video
```

安装 Python 依赖：

```bash
pip install openai pyyaml
```

安装系统依赖：

```bash
sudo apt install ffmpeg
```

配置 API Key：

```text
data/config/config.yaml
```

示例：

```yaml
DEEPSEEK_API_KEY: sk-xxxxxxxxxxxxxxxx
BAILIAN_API_KEY: sk-xxxxxxxxxxxxxxxx
```

Linux 下如果没有 `python` 命令，可以把下面命令里的 `python` 换成 `python3`。

## 3. 共同处理流程

三个模式底层都围绕四个阶段运行：

```text
mp4 + srt
  |
  v
Phase1  字幕筛选
  |
  v
Phase2  脚本组织
  |
  v
Phase3  时间轴匹配
  |
  v
Phase4  视频裁切与拼接
```

各阶段职责：

| 阶段 | 目录 | 作用 |
| --- | --- | --- |
| Phase1 | `phase1_select/` | 读取 SRT，用 prompt 从原字幕里筛出候选内容 |
| Phase2 | `phase2_rewrite/` | 基于候选内容组织最终剪辑脚本 |
| Phase3 | `phase3_match/`、`make_time/` | 把脚本句子匹配回原 SRT 时间轴，生成 `intervals.json` |
| Phase4 | `phase4_cut/`、`make_video/` | 用 FFmpeg 根据时间段裁切并拼接视频 |

常见中间文件：

```text
step1.txt        Phase1 输出
step2.txt        Phase2 输出
intervals.json   Phase3 输出
summary.json     单个视频运行摘要
events.jsonl     阶段事件日志
```

## 4. 模式一：短视频精华

入口：

```text
scripts/run_short.py
```

目标：把一个或多个长视频剪成 **60 到 150 秒** 左右的高密度短精华版。

这个模式每个输入视频只生成 1 条结果。它使用短视频专用 prompt，重点保留冲击力、核心观点、悬念、冲突、关键案例和结果，主动删除寒暄、重复铺垫和无信息增量内容。

### 4.1 输入结构

`run_short.py` 扫描一个平铺目录，目录里放同名 `.mp4` 和 `.srt`：

```text
data/video/
├── demo.mp4
├── demo.srt
├── other.mp4
└── other.srt
```

### 4.2 常用命令

处理目录下全部视频：

```bash
python scripts/run_short.py --video_dir data/video --output_dir data/output_short
```

只处理一个视频：

```bash
python scripts/run_short.py --video_dir data/video --output_dir data/output_short --video_id demo
```

输出已存在时强制重跑：

```bash
python scripts/run_short.py --video_dir data/video --output_dir data/output_short --force
```

### 4.3 输出结构

```text
data/output_short/demo/
├── step1.txt
├── step2.txt
├── intervals.json
├── demo_short.mp4
└── summary.json
```

`summary.json` 主要记录：

| 字段 | 含义 |
| --- | --- |
| `original_duration_sec` | 原始字幕总时长 |
| `selected_duration_sec` | 最终保留时长 |
| `segment_count` | 裁切片段数量 |
| `compression_ratio` | 压缩比例 |
| `duration_status` | `ok`、`too_short` 或 `too_long` |
| `output_video` | 输出视频路径 |

### 4.4 适合场景

- 想稳定地从每个视频产出 1 条短视频。
- 接受结果偏精简、偏高密度。
- 目标是短视频平台的单条短精华内容。

## 5. 模式二：5 分钟顺序压缩

入口：

```text
scripts/run_5min.py
```

目标：把长视频压缩成 **4 到 6 分钟** 左右的单条完整版本。

这个模式不追求强行打乱顺序做钩子，而是尽量保留原视频的论述顺序和叙事顺序。它适合把较长内容压缩成一条还能讲完整的版本。

### 5.1 输入结构

和短视频模式一样，输入目录是平铺结构：

```text
data/video/
├── demo.mp4
└── demo.srt
```

### 5.2 常用命令

处理目录下全部视频：

```bash
python scripts/run_5min.py --video_dir data/video --output_dir data/output_5min
```

只处理一个视频：

```bash
python scripts/run_5min.py --video_dir data/video --output_dir data/output_5min --video_id demo
```

输出已存在时强制重跑：

```bash
python scripts/run_5min.py --video_dir data/video --output_dir data/output_5min --force
```

### 5.3 过短重试机制

`run_5min.py` 会检查 Phase3 匹配出的总保留时长。

关键配置在脚本中：

```python
TARGET_SEC = 300
TARGET_MIN_SEC = 240
TARGET_MAX_SEC = 360
RETRY_TRIGGER_SEC = 220
```

逻辑：

```text
首轮 Phase1/2/3
  |
  v
计算保留时长
  |
  v
如果低于 220 秒，用扩写 prompt 重跑 Phase2/3
  |
  v
比较首轮和重试结果
  |
  v
选择更接近 5 分钟的一版进入 Phase4
```

### 5.4 输出结构

```text
data/output_5min/demo/
├── step1.txt
├── step2.txt
├── intervals.json
├── step2_retry1.txt
├── intervals_retry1.json
├── demo_5min.mp4
└── summary.json
```

如果没有触发重试，`step2_retry1.txt` 和 `intervals_retry1.json` 不一定存在。

`summary.json` 会额外记录：

| 字段 | 含义 |
| --- | --- |
| `retry_triggered` | 是否触发过短重试 |
| `retry_used` | 最终是否采用重试结果 |
| `retry_decision` | 选择首轮或重试的原因 |
| `selected_iteration` | 最终采用第几轮结果 |

### 5.5 适合场景

- 想从长内容里压出较完整的一条视频。
- 不希望做成碎片化金句集合。
- 希望结果保持原内容顺序和逻辑主线。

## 6. 模式三：单视频批量候选

入口：

```text
batch_generator.py
```

目标：每个源视频不只生成 1 条，而是生成多条候选，自动评分后输出多个较优结果。

这个模式更适合“候选生成和筛选”。它会对同一个视频多次运行 Phase1 和 Phase2，得到大量不同脚本候选，再通过 Phase3 匹配时间轴和机器评分筛选，最后生成多个候选视频。

### 6.1 输入结构

`batch_generator.py` 默认读取 `settings.py` 中的：

```python
DATA_DIR = "./data/hanbing"
```

输入目录是按视频 ID 分文件夹：

```text
data/hanbing/
└── demo/
    ├── demo.mp4
    └── demo.srt
```

### 6.2 运行命令

```bash
python batch_generator.py
```

`batch_generator.py` 不使用命令行参数，主要通过 `settings.py` 调整行为。

### 6.3 单视频批量流程

```text
扫描 DATA_DIR 下所有视频目录
  |
  v
每个视频运行 BATCH_PHASE1_COUNT 次 Phase1
  |
  v
从 Phase1 结果中随机取素材，运行 BATCH_PHASE2_COUNT 次 Phase2
  |
  v
每个 Phase2 脚本运行 Phase3，得到 intervals 候选
  |
  v
用 evaluate_quality() 做基础评分
  |
  v
可选补充视觉评分、转场评分
  |
  v
按分数、阈值和时长桶选择候选
  |
  v
生成多个候选视频
```

### 6.4 核心配置

配置位置：

```text
settings.py
```

常用配置：

| 配置 | 作用 |
| --- | --- |
| `DATA_DIR` | 输入视频目录 |
| `BATCH_RESULTS_DIR` | 批量结果输出目录 |
| `BATCH_LOG_FILE` | 批量事件日志 |
| `BATCH_PHASE1_COUNT` | 每个视频运行 Phase1 的次数 |
| `BATCH_PHASE2_COUNT` | 每个视频生成 Phase2 脚本候选的次数 |
| `BATCH_SCORE_THRESHOLD` | 候选最低分数线 |
| `BATCH_SINGLE_VIDEO_TARGET_PER_SOURCE` | 每个源视频最终生成多少条候选视频 |
| `BATCH_DURATION_BUCKETS` | 时长桶分布，用来控制候选时长比例 |
| `BATCH_VISUAL_ENABLE` | 是否启用视觉评分 |
| `BATCH_TRANSITION_ENABLE` | 是否启用转场规则评分 |

当前默认值示例：

```python
BATCH_PHASE1_COUNT = 20
BATCH_PHASE2_COUNT = 100
BATCH_SCORE_THRESHOLD = 7.0
BATCH_SINGLE_VIDEO_TARGET_PER_SOURCE = 10
BATCH_RESULTS_DIR = "./data/batch_results"
BATCH_LOG_FILE = "./data/batch_log.jsonl"
```

### 6.5 输出结构

```text
data/batch_results/demo/
├── phase1/
│   ├── step1_001.txt
│   └── ...
├── phase2/
│   ├── step2_001.txt
│   └── ...
├── phase3/
│   ├── intervals_001.json
│   └── ...
├── phase4/
│   ├── score_001.json
│   └── ...
├── phase5/
│   ├── video_001.mp4
│   └── ...
└── summary.json
```

`summary.json` 会记录本视频生成了多少 Phase1、Phase2、Phase3 成功候选、最终生成了多少视频，以及高分候选的评分和时长。

### 6.6 评分逻辑

基础评分由 `batch/scoring/evaluator.py` 负责，主要看：

| 维度 | 说明 |
| --- | --- |
| `duration_fit` | 候选时长是否合理 |
| `completeness` | 总时长和片段数是否足够支撑完整表达 |
| `transition` | 片段数量是否过多、跳切是否过碎 |
| `audio` | 当前是规则默认分 |
| `video` | 当前是基于片段数量的规则分 |

最终候选会按 `score_total`、时长和时长桶分布进行选择。

### 6.7 适合场景

- 想从一个源视频中得到多条不同版本。
- 希望自动评分后再生成高分候选。
- 能接受更长运行时间，以换取更多候选和更高命中率。

## 7. 多进程任务队列

`scripts/run_short.py` 和 `scripts/run_5min.py` 支持 JSON 任务队列，适合多个终端一起处理同一个输入目录。

初始化短视频任务：

```bash
python scripts/run_short.py --init_tasks --video_dir data/video --output_dir data/output_short
```

自动领取短视频任务：

```bash
python scripts/run_short.py --auto --video_dir data/video --output_dir data/output_short
```

5 分钟模式同理：

```bash
python scripts/run_5min.py --init_tasks --video_dir data/video --output_dir data/output_5min
python scripts/run_5min.py --auto --video_dir data/video --output_dir data/output_5min
```

默认任务文件：

```text
data/run_state/run_short_tasks.json
data/run_state/run_5min_tasks.json
```

默认 FFmpeg 锁文件：

```text
data/run_state/ffmpeg.lock
```

说明：

- `--init_tasks` 根据 `video_dir` 生成任务文件。
- 默认不覆盖已有任务文件，加 `--force` 才会重新初始化。
- `--auto` 自动领取 `pending` 任务，处理完成后更新状态。
- Phase1、Phase2、Phase3 可以并行。
- Phase4 会通过锁文件串行执行，避免多个 FFmpeg 同时占用机器资源。

## 8. 参数速查

`run_short.py` 和 `run_5min.py` 的主要参数相同：

| 参数 | 作用 |
| --- | --- |
| `--video_dir` | 输入目录，包含同名 `.mp4` 和 `.srt` |
| `--output_dir` | 输出目录 |
| `--force` | 输出已存在时重新生成 |
| `--log_root` | 运行日志归档目录 |
| `--video_id` | 只处理指定视频 |
| `--init_tasks` | 初始化任务文件 |
| `--auto` | 自动领取任务并循环处理 |
| `--task_file` | 指定任务状态 JSON 文件 |
| `--ffmpeg_lock_file` | 指定 FFmpeg 串行锁文件 |
| `--worker_id` | 可选调试标记 |

查看完整参数：

```bash
python scripts/run_short.py --help
python scripts/run_5min.py --help
```

## 9. 本地检查

不调用真实 LLM 的基础检查：

```bash
python -m compileall shared phase1_select phase2_rewrite phase3_match phase4_cut batch scripts batch_generator.py
python scripts/run_short.py --help
python scripts/run_5min.py --help
```

如果环境安装了 `pytest`：

```bash
python -m pytest tests/test_evaluator.py tests/test_filter_complex.py tests/test_time_utils.py tests/test_interval.py tests/test_mode2_parse.py
```

## 10. 常见问题

### 10.1 找不到输出视频

先看对应输出目录是否有：

```text
step1.txt
step2.txt
intervals.json
summary.json
```

缺少哪个文件，通常就是对应阶段失败。

### 10.2 `--auto` 没有任务

先初始化任务文件：

```bash
python scripts/run_short.py --init_tasks --video_dir data/video --output_dir data/output_short
```

再运行自动领取：

```bash
python scripts/run_short.py --auto --video_dir data/video --output_dir data/output_short
```

### 10.3 重新初始化任务文件

默认不覆盖已有任务文件，需要加 `--force`：

```bash
python scripts/run_short.py --init_tasks --force --video_dir data/video --output_dir data/output_short
```

### 10.4 批量模式没有生成视频

优先检查：

- `settings.DATA_DIR` 是否指向正确目录。
- 每个视频目录里是否有同名 `.mp4` 和 `.srt`。
- Phase3 是否生成了有效 `intervals_*.json`。
- 候选分数是否低于 `BATCH_SCORE_THRESHOLD`。
