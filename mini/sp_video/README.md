# sp_video

`sp_video` 是智能视频剪辑模块。

输入是一组同名的 `.mp4` 视频和 `.srt` 字幕，输出是剪辑后的视频文件，以及每个阶段的中间结果。

示例输入：

```text
data/video/demo.mp4
data/video/demo.srt
```

`demo` 就是这个视频的 `video_id`。

## 1. 功能总览

| 场景 | 入口 | 说明 |
| --- | --- | --- |
| 生成 60 到 150 秒短视频 | `scripts/run_short.py` | 短视频生产入口 |
| 生成 4 到 6 分钟视频 | `scripts/run_5min.py` | 5 分钟版本生产入口，支持过短重试 |
| 多视频目录批量生成候选并评分选优 | `batch_generator.py` | 批量生成、机器评分、视觉评分、转场评分、多视频组合 |
| 外部系统通过 JSON 调用 | `skill.py` | OpenClaw / 自动化系统入口 |
| 本地测试和报告 | `scripts/*.py`、`tests/*.py` | 测试、性能分析、报告生成 |

## 2. 环境准备

进入模块目录：

```bash
cd sp_video
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

## 3. 数据流

主流程分为四个 Phase：

```text
mp4 + srt
  |
  v
Phase1  字幕筛选
  输出 step1.txt
  |
  v
Phase2  脚本重组
  输出 step2.txt
  |
  v
Phase3  时间轴匹配
  输出 intervals.json
  |
  v
Phase4  视频裁切
  输出 mp4
```

各阶段职责：

| 阶段 | 目录 | 输入 | 输出 | 作用 |
| --- | --- | --- | --- | --- |
| Phase1 | `phase1_select/` | `.srt` | `step1.txt` | 从字幕中选出候选内容 |
| Phase2 | `phase2_rewrite/` | `step1.txt` | `step2.txt` | 把候选内容改写成剪辑脚本 |
| Phase3 | `phase3_match/` | `.srt` + `step2.txt` | `intervals.json` | 把脚本句子匹配回原字幕时间 |
| Phase4 | `phase4_cut/` | `.mp4` + `intervals.json` | 输出视频 | 用 ffmpeg 按时间段裁切并拼接 |

常见输出文件：

```text
step1.txt        Phase1 结果
step2.txt        Phase2 结果
intervals.json   Phase3 时间段
output.mp4       Phase4 视频结果
summary.json     本次运行摘要
events.jsonl     阶段日志
```

## 4. 常用入口

### 4.1 短视频模式

适用场景：把长视频剪成 60 到 150 秒左右的短视频。

```bash
python scripts/run_short.py --video_dir data/video --output_dir data/output_short
```

只跑某一个视频：

```bash
python scripts/run_short.py --video_dir data/video --output_dir data/output_short --video_id demo
```

强制覆盖已有结果：

```bash
python scripts/run_short.py --video_dir data/video --output_dir data/output_short --force
```

### 4.2 5 分钟模式

适用场景：把长视频压缩成 4 到 6 分钟左右的视频。

```bash
python scripts/run_5min.py --video_dir data/video --output_dir data/output_5min
```

只跑某一个视频：

```bash
python scripts/run_5min.py --video_dir data/video --output_dir data/output_5min --video_id demo
```

说明：

- `run_5min.py` 会检查输出时长。
- 如果结果过短，会使用扩写 prompt 再尝试生成一次。
- Phase4 使用 ffmpeg 生成视频。

### 4.3 多进程自动领取任务

适用场景：一个目录里有多个视频，希望开多个终端一起处理。

先初始化任务文件：

```bash
python scripts/run_short.py --init_tasks --video_dir data/video --output_dir data/output_short
```

再在多个终端里运行：

```bash
python scripts/run_short.py --auto --video_dir data/video --output_dir data/output_short
```

5 分钟模式同理：

```bash
python scripts/run_5min.py --init_tasks --video_dir data/video --output_dir data/output_5min
python scripts/run_5min.py --auto --video_dir data/video --output_dir data/output_5min
```

规则：

- `--init_tasks` 根据 `video_dir` 生成任务文件。
- 默认不覆盖已有任务文件。
- 加 `--force` 才会重新初始化任务文件。
- `--auto` 自动领取 `pending` 任务。
- 某个视频失败后，会标记为 `failed`，然后继续领取后面的任务。
- `--worker_id` 是可选调试标记，不影响任务分配。
- `--video_id` 是单视频直跑模式，不写任务文件。

默认任务文件：

```text
data/run_state/run_short_tasks.json
data/run_state/run_5min_tasks.json
```

默认 ffmpeg 锁文件：

```text
data/run_state/ffmpeg.lock
```

Phase1、Phase2、Phase3 可以多进程并行。Phase4 使用 ffmpeg 时会通过锁文件串行执行，避免多个 ffmpeg 同时抢占机器资源。

### 4.4 批量生成入口

适用场景：对多个视频批量生成候选，评分，选出更好的结果。

```bash
python batch_generator.py
```

`batch_generator.py` 不使用命令行参数，主要读取 `settings.py`。

核心配置：

```python
DATA_DIR = "./data/hanbing"
BATCH_RESULTS_DIR = "./data/batch_results"
BATCH_LOG_FILE = "./data/batch_log.jsonl"

BATCH_PHASE1_COUNT = 20
BATCH_PHASE2_COUNT = 100
BATCH_SCORE_THRESHOLD = 7.0
BATCH_SINGLE_VIDEO_TARGET_PER_SOURCE = 10
```

### 4.5 外部系统入口

适用场景：OpenClaw 或其他系统用子进程调用，标准输出是 JSON。

```bash
python skill.py list
python skill.py start --video_id VIDEO_ID
python skill.py phase2 --video_id VIDEO_ID --force
python skill.py generate --video_id VIDEO_ID
```

命令说明：

| 命令 | 作用 |
| --- | --- |
| `list` | 查询 OSS 视频列表并更新缓存 |
| `start` | 下载或准备视频，并执行 Phase1 |
| `phase2` | 执行 Phase2 和 Phase3 |
| `generate` | 执行 Phase4，生成并上传视频 |

自定义 Phase2 prompt：

```bash
python skill.py phase2 --video_id VIDEO_ID --prompt_file prompt.txt --force
```

## 5. run_short.py / run_5min.py 参数

| 参数 | 作用 |
| --- | --- |
| `--video_dir` | 输入目录，目录里放同名 `.mp4` 和 `.srt` |
| `--output_dir` | 输出目录 |
| `--force` | 输出已存在时重新生成 |
| `--log_root` | 运行日志归档目录 |
| `--video_id` | 只处理指定视频 |
| `--init_tasks` | 初始化任务文件 |
| `--auto` | 自动领取任务并循环处理 |
| `--task_file` | 指定任务状态 JSON 文件 |
| `--ffmpeg_lock_file` | 指定 ffmpeg 串行锁文件 |
| `--worker_id` | 可选调试标记 |

查看完整参数：

```bash
python scripts/run_short.py --help
python scripts/run_5min.py --help
```

## 6. batch 批量系统

`batch/` 是批量生成、评分、选优、多视频组合相关代码。

### 6.1 单视频批量流程

`batch_generator.py` 在默认配置下走单视频批量流程：

```text
扫描 DATA_DIR
  |
  v
每个视频多次运行 Phase1
  |
  v
每个 Phase1 结果多次运行 Phase2
  |
  v
每个 Phase2 结果运行 Phase3
  |
  v
对 intervals 做机器评分
  |
  v
可选：视觉评分、转场评分
  |
  v
按分数、时长桶、阈值选出候选
  |
  v
Phase5 生成候选视频
  |
  v
写出 summary.json
```

对应输出目录：

```text
data/batch_results/{video_id}/
├── phase1/
├── phase2/
├── phase3/
├── phase4/
├── phase5/
├── visual/
└── summary.json
```

### 6.2 多视频组合流程

打开配置：

```python
BATCH_MULTI_VIDEO_ENABLE = True
```

当 `DATA_DIR` 中至少有 2 个视频时，会进入多视频组合流程：

```text
每个视频先跑 Phase1/2/3
  |
  v
从 intervals 中提取候选片段
  |
  v
构建每个视频的片段池
  |
  v
组合主视频和副视频片段
  |
  v
对组合结果评分
  |
  v
按时长和分数选出候选
  |
  v
生成多视频混剪结果
```

输出目录：

```text
data/batch_results/multi_video/
├── summary.json
└── generated_videos/
```

### 6.3 batch 配置项

| 配置 | 作用 |
| --- | --- |
| `BATCH_PHASE1_COUNT` | 每个视频运行 Phase1 的次数 |
| `BATCH_PHASE2_COUNT` | Phase2 总生成次数 |
| `BATCH_SCORE_THRESHOLD` | 候选最低分数线 |
| `BATCH_SINGLE_VIDEO_TARGET_PER_SOURCE` | 每个源视频最终保留多少个单视频候选 |
| `BATCH_DURATION_BUCKETS` | 时长桶分布，用来控制短、中、长候选比例 |
| `BATCH_VISUAL_ENABLE` | 是否启用视觉评分流程 |
| `BATCH_VISUAL_USE_LLM` | 视觉评分是否调用多模态 LLM |
| `BATCH_VISUAL_TOPN` | 对前几个候选补视觉评分 |
| `BATCH_TRANSITION_ENABLE` | 是否启用转场规则评分 |
| `BATCH_MULTI_VIDEO_ENABLE` | 是否启用多视频组合 |
| `BATCH_MIN_MULTI_VIDEO_DURATION_SEC` | 多视频候选最小时长 |
| `BATCH_MULTI_VIDEO_TARGET_COUNT` | 多视频最终目标候选数 |
| `BATCH_MULTI_VIDEO_CANDIDATE_COUNT` | 多视频组合候选生成上限 |
| `BATCH_TEST_MODE` | 测试模式，降低 Phase1/Phase2 次数 |

### 6.4 batch 文件职责

| 文件 | 作用 |
| --- | --- |
| `batch/runner/phase_runner.py` | 批量运行 Phase1、Phase2、Phase3 |
| `batch/scoring/evaluator.py` | 基础机器评分，关注时长、完整度等 |
| `batch/scoring/transition_scorer.py` | 转场规则评分，判断片段是否太碎、跳跃是否明显 |
| `batch/scoring/visual_scorer.py` | 视觉评分入口，可结合抽帧和多模态 LLM |
| `batch/scoring/frame_sampler.py` | 从视频中抽帧 |
| `batch/scoring/image_grid.py` | 把抽出的帧拼成九宫格 |
| `batch/multi_video/selector.py` | 构建多视频输入结构 |
| `batch/multi_video/pool_builder.py` | 把单视频 intervals 转成候选片段池 |
| `batch/multi_video/combiner.py` | 组合多视频候选 |
| `batch/multi_video/scorer.py` | 给多视频组合结果评分 |
| `batch/debug/visual_debug.py` | 生成视觉评分调试报告 |
| `batch/debug/visual_debug_standalone.py` | 独立运行视觉调试 |

## 7. 代码结构

```text
sp_video/
├── batch_generator.py
├── skill.py
├── settings.py
├── phase1_select/
├── phase2_rewrite/
├── phase3_match/
├── phase4_cut/
├── batch/
├── shared/
├── scripts/
├── make_time/
├── make_video/
└── tests/
```

### 7.1 顶层文件

| 文件 | 作用 |
| --- | --- |
| `batch_generator.py` | 批量生成、评分、选优入口 |
| `skill.py` | 外部系统 JSON 调用入口，包含 OSS 下载、状态缓存、上传逻辑 |
| `settings.py` | 全局配置中心 |
| `ARCHITECTURE.md` | 架构说明 |
| `CLAUDE.md` | 协作和上下文说明 |
| `skill_README.md` | `skill.py` 相关说明 |
| `TEST.md` | 测试说明 |

### 7.2 Phase 文件

| 文件 | 作用 |
| --- | --- |
| `phase1_select/prompts.py` | Phase1 prompt |
| `phase1_select/runner.py` | Phase1 单次和批量调用 |
| `phase2_rewrite/prompts.py` | Phase2 prompt，包括 video、5min、short 等模式 |
| `phase2_rewrite/runner.py` | Phase2 单次和批量调用 |
| `phase3_match/runner.py` | Phase3 时间轴匹配封装 |
| `phase4_cut/runner.py` | Phase4 视频裁切封装 |

### 7.3 shared 公共工具

| 文件 | 作用 |
| --- | --- |
| `shared/llm_caller.py` | LLM 批量调用和流式调用 |
| `shared/logger.py` | `BatchLogger`，写入阶段日志和事件日志 |
| `shared/output.py` | `info`、`warn`、`error`、`debug` 输出函数 |
| `shared/utils.py` | 通用小工具 |
| `shared/file_lock.py` | 跨进程文件锁，用于 ffmpeg 串行 |
| `shared/task_queue.py` | JSON 任务队列，支持初始化、领取、更新任务 |

### 7.4 scripts 脚本

| 文件 | 作用 |
| --- | --- |
| `scripts/run_short.py` | 短视频生产入口 |
| `scripts/run_5min.py` | 5 分钟视频生产入口 |
| `scripts/run_batch_experiments.py` | 批量实验脚本 |
| `scripts/run_comprehensive_test.py` | 综合测试脚本 |
| `scripts/run_all_tests.py` | 测试集合入口 |
| `scripts/analyze_performance.py` | 性能分析 |
| `scripts/generate_test_report.py` | 生成测试报告 |
| `scripts/verify_multi_video_builder_example.py` | 多视频生成示例验证 |

### 7.5 make_time 旧时间轴模块

这些文件是 Phase3 底层实现的一部分，当前第一轮重构中保留。

| 文件 | 作用 |
| --- | --- |
| `make_time/ai_caller.py` | 旧 AI 调用辅助 |
| `make_time/chat.py` | 旧对话调用逻辑 |
| `make_time/interval.py` | 时间段结构和处理 |
| `make_time/mode2.py` | 旧模式 2 解析和匹配逻辑 |
| `make_time/prompts.py` | 旧时间轴相关 prompt |
| `make_time/step2.py` | 时间轴匹配主逻辑 |
| `make_time/time_utils.py` | 时间格式转换工具 |

### 7.6 make_video 旧视频生成模块

这些文件是 Phase4 底层实现的一部分，当前第一轮重构中保留。

| 文件 | 作用 |
| --- | --- |
| `make_video/filter_builder.py` | ffmpeg filter_complex 构建 |
| `make_video/multi_video_builder.py` | 多视频混剪生成 |
| `make_video/step3.py` | 旧视频裁切主逻辑 |

### 7.7 tests 测试文件

| 文件 | 作用 |
| --- | --- |
| `tests/test_batch_generator.py` | 批量入口相关测试 |
| `tests/test_evaluator.py` | 评分逻辑测试 |
| `tests/test_filter_complex.py` | ffmpeg filter 构建测试 |
| `tests/test_interval.py` | 时间段处理测试 |
| `tests/test_mode2_parse.py` | 旧 mode2 解析测试 |
| `tests/test_multi_video_builder.py` | 多视频生成测试 |
| `tests/test_step3.py` | 旧视频裁切逻辑测试 |
| `tests/test_time_utils.py` | 时间工具测试 |

## 8. 本地检查

不调用真实 LLM 的静态检查：

```bash
python -m compileall shared phase1_select phase2_rewrite phase3_match phase4_cut batch scripts skill.py batch_generator.py
python scripts/run_short.py --help
python scripts/run_5min.py --help
python skill.py --help
```

如果环境里安装了 `pytest`：

```bash
python -m pytest tests/test_evaluator.py tests/test_filter_complex.py tests/test_time_utils.py tests/test_interval.py tests/test_mode2_parse.py
```

## 9. 常见问题

### 9.1 找不到输出视频

先看输出目录是否有：

```text
step1.txt
step2.txt
intervals.json
summary.json
events.jsonl
```

缺少哪个文件，通常就是对应阶段失败。

### 9.2 `--auto` 没有任务

先初始化任务：

```bash
python scripts/run_short.py --init_tasks --video_dir data/video --output_dir data/output_short
```

再启动自动领取：

```bash
python scripts/run_short.py --auto --video_dir data/video --output_dir data/output_short
```

### 9.3 重新初始化任务文件

默认不覆盖已有任务文件。需要加 `--force`：

```bash
python scripts/run_short.py --init_tasks --force --video_dir data/video --output_dir data/output_short
```

### 9.4 batch 没有生成多视频结果

检查：

```python
BATCH_MULTI_VIDEO_ENABLE = True
```

同时确认 `DATA_DIR` 下至少有两个有效视频，每个视频目录里都有同名 `.mp4` 和 `.srt`。

### 9.5 import 路径变更

新的 batch 路径：

```python
from batch.scoring.evaluator import evaluate_quality
from batch.runner.phase_runner import run_phase1_loop
from batch.multi_video.combiner import build_multi_video_candidates
```

不要再使用旧路径：

```python
from batch.evaluator import evaluate_quality
from batch.phase_runner import run_phase1_loop
from batch.video_combiner import build_multi_video_candidates
```
