# sp_video

`sp_video` 是智能视频剪辑工程。输入 `mp4 + srt`，经过字幕筛选、脚本重组、时间轴匹配和 ffmpeg 裁剪，输出剪辑后的视频。

重构后，主业务按四个 phase 组织；批量生成、评分、选优放在 `batch/`；公共工具放在 `shared/`。

## 安装

```bash
pip install openai pyyaml
```

系统需要安装 FFmpeg / FFprobe：

```bash
sudo apt install ffmpeg
```

## 配置

在 `data/config/config.yaml` 中填写 API Key：

```yaml
DEEPSEEK_API_KEY: sk-xxxxxxxxxxxxxxxx
BAILIAN_API_KEY: sk-xxxxxxxxxxxxxxxx
```

## 目录结构

```text
sp_video/
├── main.py                  # CLI 入口，只做参数解析和流程调度
├── batch_generator.py       # 批量生成主入口
├── skill.py                 # OpenClaw / 外部系统 JSON 调用入口
├── settings.py              # 全局配置
│
├── phase1_select/           # Phase1: SRT -> 候选字幕文本
├── phase2_rewrite/          # Phase2: 候选字幕 -> 重组脚本
├── phase3_match/            # Phase3: 脚本 + SRT -> 时间轴 intervals
├── phase4_cut/              # Phase4: intervals + mp4 -> 输出视频
│
├── batch/
│   ├── runner/              # 批量跑 Phase1/2/3
│   ├── scoring/             # 单视频候选评分
│   ├── multi_video/         # 多视频片段池、组合、评分
│   └── debug/               # 调试脚本
│
├── shared/                  # LLM、日志、输出、通用工具
├── scripts/                 # 人直接运行的脚本入口
├── make_time/               # 旧时间轴匹配实现，第一轮重构暂保留
└── make_video/              # 旧视频裁剪实现，第一轮重构暂保留
```

## 数据流程

```text
输入: video.mp4 + video.srt
        │
        ▼
[Phase 1] phase1_select
LLM 从 SRT 中筛选候选字幕 -> step1.txt
        │
        ▼
[Phase 2] phase2_rewrite
LLM 根据候选字幕重组脚本 -> step2.txt
        │
        ▼
[Phase 3] phase3_match
脚本匹配回原 SRT 时间轴 -> intervals.json
        │
        ▼
[Phase 4] phase4_cut
ffmpeg 按时间段裁剪 -> output.mp4
```

## 新人阅读地图

| 想做什么 | 去哪里看 |
|----------|----------|
| 改 Phase1 筛字幕 prompt | `phase1_select/prompts.py` |
| 看 Phase1 怎么调用 LLM | `phase1_select/runner.py` |
| 改 Phase2 重组脚本 prompt | `phase2_rewrite/prompts.py` |
| 看 Phase2 怎么生成脚本 | `phase2_rewrite/runner.py` |
| 看脚本如何匹配回 SRT 时间轴 | `phase3_match/runner.py` |
| 看视频如何按时间段裁剪 | `phase4_cut/runner.py` |
| 看 5 分钟版单视频入口 | `scripts/run_5min.py` |
| 看短精华版单视频入口 | `scripts/run_short.py` |
| 看批量候选怎么生成 | `batch/runner/phase_runner.py` |
| 看候选怎么评分 | `batch/scoring/` |
| 看多视频怎么组合 | `batch/multi_video/` |
| 看外部系统调用入口 | `skill.py` |
| 看批量主入口 | `batch_generator.py` |
| 看 LLM 调用、日志、通用工具 | `shared/` |

## 主要入口

### 1. CLI 单视频入口

```bash
cd sp_video
python main.py --input_video data/hanbing/VIDEO_ID/VIDEO_ID.mp4 --input_srt data/hanbing/VIDEO_ID/VIDEO_ID.srt --stage 4
```

阶段说明：

- `--stage 1`：只生成 `step1.txt`
- `--stage 2`：生成到 `step2.txt`
- `--stage 3`：生成到 `intervals.json`
- `--stage 4`：完整生成视频

### 2. 5 分钟版单视频压缩

```bash
cd sp_video
python scripts/run_5min.py --video_dir data/video --output_dir data/output_5min
```

说明：

- 输入目录需要包含同名 `.mp4` 和 `.srt`
- 目标输出约 4 到 6 分钟
- 结果过短时会用扩展 prompt retry

常用参数：

```bash
python scripts/run_5min.py --video_dir data/video --output_dir data/output_5min --force
```

### 3. 短精华版单视频压缩

```bash
cd sp_video
python scripts/run_short.py --video_dir data/video --output_dir data/output_short
```

说明：

- 输入目录需要包含同名 `.mp4` 和 `.srt`
- 目标输出约 60 到 150 秒
- 不含 retry

### 4. 批量生成入口

```bash
cd sp_video
python batch_generator.py
```

说明：

- 使用 `settings.DATA_DIR` 扫描视频
- 批量跑 Phase1/2/3
- 在 `batch/scoring/` 中评分
- 最后生成候选视频

测试模式可以在 `settings.py` 中打开：

```python
BATCH_TEST_MODE = True
BATCH_TEST_PHASE1_COUNT = 3
BATCH_TEST_PHASE2_COUNT = 20
```

### 5. OpenClaw / 外部系统入口

```bash
cd sp_video
python skill.py list
python skill.py start --video_id VIDEO_ID
python skill.py phase2 --video_id VIDEO_ID --force
python skill.py generate --video_id VIDEO_ID
```

`skill.py` 不再依赖 `main.py`。自定义 Phase2 prompt 通过 `--prompt_file` 传入：

```bash
python skill.py phase2 --video_id VIDEO_ID --prompt_file prompt.txt --force
```

## 不触发 LLM 的本地检查

拉代码后可以先做静态检查：

```bash
cd sp_video
python -m compileall shared phase1_select phase2_rewrite phase3_match phase4_cut batch scripts main.py skill.py batch_generator.py
```

检查入口参数：

```bash
python main.py --help
python scripts/run_5min.py --help
python scripts/run_short.py --help
python skill.py --help
```

检查 import：

```bash
python -c "import main; import batch_generator; import skill; from batch.runner.phase_runner import run_phase1_loop; from batch.scoring.evaluator import evaluate_quality; from batch.multi_video.selector import build_video_sources; print('imports ok')"
```

这些命令不会调用真实 LLM。

## pytest 检查

如果测试环境安装了 `pytest`，可以先跑不依赖真实 LLM 的测试：

```bash
cd sp_video
python -m pytest tests/test_evaluator.py tests/test_filter_complex.py tests/test_time_utils.py tests/test_interval.py tests/test_mode2_parse.py
```

更多测试需要确认测试数据、FFmpeg/FFprobe、配置文件都存在。

## 真实业务验收建议

真实验收建议按以下顺序：

```bash
cd sp_video

python scripts/run_short.py --video_dir data/video --output_dir data/output_short --force
python scripts/run_5min.py --video_dir data/video --output_dir data/output_5min --force
python batch_generator.py
```

如果要验收外部调用入口：

```bash
python skill.py list
python skill.py start --video_id VIDEO_ID
python skill.py phase2 --video_id VIDEO_ID --force
python skill.py generate --video_id VIDEO_ID
```

验收重点：

- 是否生成 `step1.txt`
- 是否生成 `step2.txt`
- 是否生成 `intervals.json`
- 是否生成最终 `.mp4`
- `summary.json` 字段是否完整
- `events.jsonl` 是否记录 phase 成功/失败和耗时
- 5min 模式是否保留 heartbeat 和 retry 日志
- batch 模式是否能生成候选并评分

## 常见问题

### 找不到 batch.evaluator 等旧路径

重构后路径已经变化：

```python
from batch.scoring.evaluator import evaluate_quality
from batch.runner.phase_runner import run_phase1_loop
from batch.multi_video.combiner import build_multi_video_candidates
```

不要再使用：

```python
from batch.evaluator import evaluate_quality
from batch.phase_runner import run_phase1_loop
from batch.video_combiner import build_multi_video_candidates
```

### 不要从 main.py import 业务函数

重构后 `main.py` 只是 CLI wrapper。业务代码应该直接 import phase：

```python
from phase1_select.runner import run_phase1
from phase2_rewrite.runner import run_phase2
from phase3_match.runner import run_phase3
from phase4_cut.runner import run_phase4
```

### 不想跑真实 LLM

只跑静态检查：

```bash
python -m compileall ...
python xxx.py --help
python -c "import ..."
```

不要运行真实业务入口：

```bash
python scripts/run_short.py ...
python scripts/run_5min.py ...
python batch_generator.py
python skill.py start ...
python skill.py phase2 ...
```

