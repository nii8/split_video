# sp_video 重构方案（融合 sp_mini）

## 目标

把 sp_mini 的功能融合进 sp_video，只维护一个工程。
目录结构清晰对应处理流程的四个阶段。

---

## 目标目录结构

```
sp_video/
│
├── settings.py                        # 全局配置（不变）
│
├── phase1_select/                     # Phase1：SRT → 候选字幕文本
│   ├── __init__.py
│   ├── prompts.py                     # 3套prompt：
│   │                                  #   PROMPT_VIDEO   （原sp_video风格，短视频爆款）
│   │                                  #   PROMPT_5MIN    （原sp_mini版，5分钟顺序压缩）
│   │                                  #   PROMPT_SHORT   （原sp_mini版，短精华）
│   └── runner.py                      # run_phase1(srt_path, prompt) → str
│
├── phase2_rewrite/                    # Phase2：候选字幕 → 重组脚本
│   ├── __init__.py
│   ├── prompts.py                     # 4套prompt：
│   │                                  #   PROMPT_VIDEO        （sp_video版）
│   │                                  #   PROMPT_5MIN         （sp_mini版）
│   │                                  #   PROMPT_5MIN_EXPAND  （sp_mini retry版）
│   │                                  #   PROMPT_SHORT        （sp_mini版）
│   └── runner.py                      # run_phase2(phase1_text, prompt) → str
│
├── phase3_match/                      # Phase3：脚本文本+SRT → AI匹配 → 时间轴
│   ├── __init__.py
│   └── runner.py                      # get_keep_intervals(srt_path, script) → intervals
│                                      # 内部调用现有 make_time/ 逻辑（暂保留）
│
├── phase4_cut/                        # Phase4：intervals+mp4 → 输出视频
│   ├── __init__.py
│   └── runner.py                      # cut_video(mp4_path, output_path, segments)
│                                      # 内部调用现有 make_video/ 逻辑（暂保留）
│
├── shared/                            # 公共工具（不属于任何phase）
│   ├── __init__.py
│   ├── llm_caller.py                  # call_llm_batch / call_llm_stream
│   │                                  # 从 main.py 提取，统一管理LLM调用
│   └── logger.py                      # BatchLogger，从 batch/logger.py 迁入
│
├── batch/                             # sp_video独有：批量生成 + 评分 + 选优
│   ├── runner/
│   │   └── phase_runner.py            # [执行层] 批量跑Phase1/2/3，生成候选池
│   │
│   ├── scoring/
│   │   ├── evaluator.py               # [评分层] 基础机器评分（时长/完整度）
│   │   ├── transition_scorer.py       # [评分层] 转场规则评分（片段碎/跳跃）
│   │   ├── visual_scorer.py           # [评分层] 视觉LLM评分（多模态看画面）
│   │   ├── frame_sampler.py           # [评分层] 从mp4抽帧（供visual_scorer用）
│   │   └── image_grid.py              # [评分层] 把帧拼成9宫格（供visual_scorer用）
│   │
│   ├── multi_video/
│   │   ├── selector.py                # [多视频组合层] 构建多视频输入结构
│   │   ├── pool_builder.py            # [多视频组合层] 构建单视频候选片段池
│   │   ├── combiner.py                # [多视频组合层] 主+副视频组合成候选
│   │   └── scorer.py                  # [多视频组合层] 给多视频组合评分
│   │
│   └── debug/
│       └── visual_debug.py            # [调试层] 视觉评分过程可视化报告
│
├── scripts/                           # 入口脚本
│   ├── run_5min.py                    # 5分钟版批处理（从sp_mini搬来，改import）
│   │                                  # 含 ProgressTracker + retry 机制
│   └── run_short.py                   # 短精华版批处理（从sp_mini搬来，改import）
│
├── batch_generator.py                 # sp_video批量主入口（改import）
└── skill.py                           # OpenClaw子进程JSON接口（改import）
```

---

## 数据流程

### sp_mini 模式（单视频压缩）
```
video.srt + video.mp4
    ↓
[Phase1] phase1_select/runner.py  （使用 PROMPT_5MIN 或 PROMPT_SHORT）
    LLM筛选候选字幕 → step1.txt
    ↓
[Phase2] phase2_rewrite/runner.py  （使用对应prompt，5min版含retry）
    LLM重组脚本 → step2.txt
    ↓
[Phase3] phase3_match/runner.py   （两种模式共享）
    AI匹配 → intervals.json
    ↓
[Phase4] phase4_cut/runner.py     （两种模式共享）
    ffmpeg剪辑 → output.mp4
```

### sp_video 模式（批量生成+评分选优）
```
video.srt + video.mp4
    ↓
[Phase1 ×20次] phase1_select/runner.py  （使用 PROMPT_VIDEO）
    批量筛选 → step1_001.txt ... step1_020.txt
    ↓
[Phase2 ×100次] phase2_rewrite/runner.py
    批量重组 → step2_001.txt ... step2_100.txt
    ↓
[Phase3 ×100次] phase3_match/runner.py
    批量AI匹配 → intervals_001.json ...
    ↓
[评分] batch/scoring/evaluator.py + batch/scoring/transition_scorer.py + batch/scoring/visual_scorer.py（可选）
    → 每个candidate得分
    ↓
[选优/组合] batch/multi_video/combiner.py
    单视频取最高分 / 多视频组合
    ↓
[Phase4] phase4_cut/runner.py
    ffmpeg剪辑 → output.mp4
```

---

## 改动清单

### 新建文件

| 文件 | 来源 |
|------|------|
| `phase1_select/__init__.py` | 新建空文件 |
| `phase1_select/prompts.py` | 合并：sp_video的PHASE1_PROMPT + sp_mini的PROMPT_5MIN + PROMPT_SHORT |
| `phase1_select/runner.py` | 从 main.py 提取 run_phase1 逻辑 |
| `phase2_rewrite/__init__.py` | 新建空文件 |
| `phase2_rewrite/prompts.py` | 合并：sp_video的PHASE2_PROMPT + sp_mini的三套prompt |
| `phase2_rewrite/runner.py` | 从 main.py 提取 run_phase2 逻辑 |
| `phase3_match/__init__.py` | 新建空文件 |
| `phase3_match/runner.py` | 包装 make_time.step2.get_keep_intervals |
| `phase4_cut/__init__.py` | 新建空文件 |
| `phase4_cut/runner.py` | 包装 make_video.step3.cut_video |
| `shared/__init__.py` | 新建空文件 |
| `shared/llm_caller.py` | 从 main.py 提取 call_llm_batch / call_llm_stream |
| `shared/logger.py` | 从 batch/logger.py 迁入（内容不变） |
| `scripts/run_5min.py` | 从 sp_mini/scripts/run_single_video_5min_batch.py 搬来，改import |
| `scripts/run_short.py` | 从 sp_mini/scripts/run_single_video_short_batch.py 搬来，改import |

### 移动并修改 import 的文件

| 文件 | 改动 |
|------|------|
| `batch/runner/phase_runner.py` | 不再 import main.py，改从 phase1_select/runner, phase2_rewrite/runner, shared/llm_caller |
| `batch/scoring/evaluator.py` | 从 `batch/evaluator.py` 移入 scoring，逻辑不变 |
| `batch/scoring/transition_scorer.py` | 从 `batch/transition_scorer.py` 移入 scoring，逻辑不变 |
| `batch/scoring/visual_scorer.py` | 从 `batch/visual_scorer.py` 移入 scoring，更新 frame/image_grid import |
| `batch/scoring/frame_sampler.py` | 从 `batch/frame_sampler.py` 移入 scoring，逻辑不变 |
| `batch/scoring/image_grid.py` | 从 `batch/image_grid.py` 移入 scoring，逻辑不变 |
| `batch/multi_video/selector.py` | 从 `batch/multi_video_selector.py` 移入 multi_video，逻辑不变 |
| `batch/multi_video/pool_builder.py` | 从 `batch/video_pool_builder.py` 移入 multi_video，逻辑不变 |
| `batch/multi_video/combiner.py` | 从 `batch/video_combiner.py` 移入 multi_video，逻辑不变 |
| `batch/multi_video/scorer.py` | 从 `batch/multi_video_scorer.py` 移入 multi_video，逻辑不变 |
| `batch/debug/visual_debug.py` | 从 `batch/visual_debug.py` 移入 debug，更新 visual_scorer import |
| `batch_generator.py` | 改从新的 phase 模块 import |
| `skill.py` | 改从新的 phase 模块 import |

### 删除文件

| 文件 | 原因 |
|------|------|
| `main.py` | 职责全部分散到各 phase 目录和 shared/ |

### 暂时保留不动

- `make_time/`：phase3_match/runner.py 内部调用它，待后续整理
- `make_video/`：phase4_cut/runner.py 内部调用它，待后续整理
- `batch/` 下所有文件：按 runner/scoring/multi_video/debug 分层移动，除 import 路径外逻辑不动

---

## Import 路径变化示例

```python
# 改之前（batch/phase_runner.py）
from main import run_phase1_batch, run_phase2_batch
from make_time.step2 import get_keep_intervals

# 改之后（batch/runner/phase_runner.py）
from phase1_select.runner import run_phase1
from phase2_rewrite.runner import run_phase2
from phase3_match.runner import get_keep_intervals
from shared.llm_caller import call_llm_batch

# 改之前（batch_generator.py）
from batch.phase_runner import run_phase1_loop, run_phase2_loop, run_phase3_loop
from batch.evaluator import evaluate_quality
from batch.visual_scorer import enrich_top_interval_candidates_with_visual_score
from batch.transition_scorer import enrich_candidates_with_transition_score
from batch.video_pool_builder import keep_intervals_to_segments
from batch.video_combiner import build_multi_video_candidates
from batch.multi_video_scorer import score_multi_video_candidate, merge_multi_video_score

# 改之后（batch_generator.py）
from batch.runner.phase_runner import run_phase1_loop, run_phase2_loop, run_phase3_loop
from batch.scoring.evaluator import evaluate_quality
from batch.scoring.visual_scorer import enrich_top_interval_candidates_with_visual_score
from batch.scoring.transition_scorer import enrich_candidates_with_transition_score
from batch.multi_video.pool_builder import keep_intervals_to_segments
from batch.multi_video.combiner import build_multi_video_candidates
from batch.multi_video.scorer import score_multi_video_candidate, merge_multi_video_score

# 改之前（scripts/run_5min.py，来自sp_mini）
from main import run_phase1_batch, run_phase2_batch, call_llm_batch
from make_time.step2 import get_keep_intervals
from make_video.step3 import cut_video
from batch.logger import BatchLogger

# 改之后
from phase1_select.runner import run_phase1
from phase2_rewrite.runner import run_phase2
from phase3_match.runner import get_keep_intervals
from phase4_cut.runner import cut_video
from shared.llm_caller import call_llm_batch
from shared.logger import BatchLogger
from phase1_select.prompts import PROMPT_5MIN
from phase2_rewrite.prompts import PROMPT_5MIN, PROMPT_5MIN_EXPAND
```

---

## 执行顺序

1. 创建 `shared/`，迁入 llm_caller、logger
2. 创建 `phase1_select/`，合并所有Phase1 prompts，提取runner
3. 创建 `phase2_rewrite/`，合并所有Phase2 prompts，提取runner
4. 创建 `phase3_match/runner.py`（包装make_time调用）
5. 创建 `phase4_cut/runner.py`（包装make_video调用）
6. 把 sp_mini 的两个批处理脚本搬进 `scripts/`，改import
7. 移动并更新 `batch/runner/phase_runner.py`、`batch_generator.py`、`skill.py` 的 import
8. 删除 `main.py`
9. 验证：跑 scripts/run_5min.py 和 batch_generator.py

---

## 注意事项

1. **settings.py 各自独立**：sp_mini 和 sp_video 的配置不同，只保留 sp_video 的 settings.py
2. **call_llm_batch 函数差异**：sp_mini 的版本有 heartbeat_callback 参数，sp_video 的没有 → shared/llm_caller.py 采用 sp_mini 版本（含 heartbeat_callback，向下兼容）
3. **运行路径**：在 sp_video/ 目录下运行，`PYTHONPATH=.` 或直接 python -m 方式执行

---

## 融合重构主线

`architecture_refactor.md` 是 sp_mini 的单工程整理方案；本文件才是主目标：**把 sp_mini 的 5min / short 单视频压缩能力融合进 sp_video，并保留 sp_video 已有的批量生成、评分、选优、多视频能力。**

重构后的维护原则：

1. `sp_video` 是唯一主工程，后续新增能力都进 `sp_video/`
2. `sp_mini` 只作为迁移来源和历史对照，不再继续演进
3. 四个 phase 是公共处理骨架，所有模式只通过 prompt、循环次数、时长目标、输出目录策略体现差异
4. `batch/` 仍然表示 sp_video 独有的“候选池 + 评分 + 选优”能力，不并入 phase
5. 第一轮重构优先降低风险：先新增包装层和兼容入口，再切换调用方，最后再考虑删除旧入口

---

## 三种运行模式

融合后 `sp_video` 至少要同时支持三种模式：

| 模式 | 来源 | 目标 | Phase1/2 prompt | Phase3/4 | 输出特征 |
|------|------|------|-----------------|----------|----------|
| `video` | 原 sp_video | 批量生成短视频候选并评分选优 | `PROMPT_VIDEO` | 共用 | 多候选、评分、可多视频组合 |
| `5min` | 原 sp_mini | 单视频顺序压缩到约 4-6 分钟 | `PROMPT_5MIN` + `PROMPT_5MIN_EXPAND` | 共用 | 单结果、带 retry、进度 heartbeat |
| `short` | 原 sp_mini | 单视频压缩成高密度短精华 | `PROMPT_SHORT` | 共用 | 单结果、无 retry、目标约 60-150 秒 |

这三种模式不要复制三套 phase 逻辑。推荐做法是引入轻量的模式配置：

```python
MODE_VIDEO = {
    "name": "video",
    "phase1_prompt": PROMPT_VIDEO,
    "phase2_prompt": PROMPT_VIDEO,
}

MODE_5MIN = {
    "name": "5min",
    "phase1_prompt": PROMPT_5MIN,
    "phase2_prompt": PROMPT_5MIN,
    "phase2_retry_prompt": PROMPT_5MIN_EXPAND,
    "target_sec": 300,
    "target_min_sec": 240,
    "target_max_sec": 360,
}

MODE_SHORT = {
    "name": "short",
    "phase1_prompt": PROMPT_SHORT,
    "phase2_prompt": PROMPT_SHORT,
    "target_sec": 90,
    "target_min_sec": 60,
    "target_max_sec": 150,
}
```

第一轮可以不单独建 `modes.py`，但代码结构要朝这个方向收敛，避免把 `5min` / `short` 的差异散落到多个脚本里。

---

## 现状依赖梳理

当前关键倒置依赖：

| 当前文件 | 当前依赖 | 问题 | 目标 |
|----------|----------|------|------|
| `batch/runner/phase_runner.py` | `from main import run_phase1_batch, run_phase2_batch` | 批量执行层依赖 CLI 入口 | 改依赖 `phase1_select.runner` / `phase2_rewrite.runner` |
| `batch_generator.py` | `make_video.step3.cut_video_main` | 输出路径被 `cut_video_main` 写死到 `data/hanbing` | 改依赖 `phase4_cut.runner`，显式传输出路径 |
| `skill.py` | `from main import run_phase1, run_phase2, run_phase3, run_phase4, PHASE2_PROMPT` | 技能入口依赖 CLI 全局变量，还会临时修改 `main.PHASE2_PROMPT` | 改成给 `run_phase2` 传 prompt 参数 |
| `sp_mini/scripts/run_single_video_5min_batch.py` | `from main import ...` | 5min 脚本倒挂 `sp_mini/main.py` | 搬进 `sp_video/scripts/run_5min.py` 后依赖 phase/shared |
| `sp_mini/scripts/run_single_video_short_batch.py` | 自带 prompt 和 LLM 调用 | 与 main.py 重复 | 搬进 `sp_video/scripts/run_short.py` 后依赖 phase/shared |

`main.py` 不建议在第一步直接删除。更稳的顺序是：

1. 新建 phase/shared 模块
2. 修改 `batch/runner/phase_runner.py`、`batch_generator.py`、`skill.py` 依赖新模块
3. 让 `main.py` 变成薄 CLI 包装，内部调用新模块
4. 验证通过后，再决定保留兼容 CLI 还是删除

---

## 分阶段实施计划

### P0：冻结行为与建立验收基线

目标：先知道“现在能跑什么”，避免重构后无从判断是否退化。

任务：

1. 记录当前 `sp_video` 的入口：`batch_generator.py`、`skill.py`、`main.py`
2. 记录当前 `sp_mini` 的入口：`run_single_video_5min_batch.py`、`run_single_video_short_batch.py`
3. 给无 LLM 的纯函数测试先跑一遍：`test_time_utils.py`、`test_filter_complex.py`、`test_interval.py`、`test_mode2_parse.py`
4. 明确含 LLM / ffmpeg / OSS 的测试只做手动验收，不作为第一轮自动测试阻塞项

验收：

- 能列出当前所有入口和对应命令
- 能确认现有纯函数测试基线
- 文档记录已知无法自动验收的外部依赖

### P1：抽出 shared，但不改变业务调用

目标：先把公共能力集中起来，但保持现有入口行为不变。

新建：

| 文件 | 内容 |
|------|------|
| `shared/__init__.py` | 空文件 |
| `shared/llm_caller.py` | 采用 sp_mini 的 `call_llm_batch(prompt, heartbeat_callback=None)`，同时提供 `call_llm_stream(prompt)` |
| `shared/logger.py` | 从 `batch/logger.py` 复制或迁移 `BatchLogger` |
| `shared/output.py` | 从 `sp_mini/batch/output.py` 迁入，供 5min / short 脚本使用 |
| `shared/utils.py` | 放 `TeeStream`、`make_run_id`、`find_video_pairs`、`keep_intervals_to_segments` 等重复工具 |

注意：

- `shared/llm_caller.py` 第一轮继续用 `settings.BAILIAN_API_KEY` 和 `qwen3.5-plus`
- `heartbeat_callback` 参数必须保留，给 5min 进度输出使用
- `batch/logger.py` 可暂时保留，后续再改成兼容 re-export

验收：

- `python -m compileall shared` 通过
- 原入口还没有切换时，行为不变

### P2：抽出 Phase1 / Phase2 prompt 与 runner

目标：解除 `batch/runner/phase_runner.py`、`skill.py` 对 `main.py` 的依赖。

新建：

| 文件 | 内容 |
|------|------|
| `phase1_select/prompts.py` | `PROMPT_VIDEO`、`PROMPT_5MIN`、`PROMPT_SHORT` |
| `phase1_select/runner.py` | `run_phase1(...)`、`run_phase1_batch(...)` |
| `phase2_rewrite/prompts.py` | `PROMPT_VIDEO`、`PROMPT_5MIN`、`PROMPT_5MIN_EXPAND`、`PROMPT_SHORT` |
| `phase2_rewrite/runner.py` | `run_phase2(...)`、`run_phase2_batch(...)` |

建议函数签名：

```python
def run_phase1(srt_path, prompt, output_dir=None, output_path=None, interactive=False, stream=False, heartbeat_callback=None):
    ...

def run_phase2(phase1_text, prompt, output_dir=None, output_path=None, interactive=False, stream=False, heartbeat_callback=None):
    ...
```

兼容包装：

```python
def run_phase1_batch(video_id, srt_path, output_path, prompt=PROMPT_VIDEO, heartbeat_callback=None):
    ...

def run_phase2_batch(video_id, phase1_content, output_path, prompt=PROMPT_VIDEO, heartbeat_callback=None):
    ...
```

注意：

- `video_id` 在 Phase1/2 里实际不参与逻辑，可以保留为兼容参数
- `skill.py` 的自定义 prompt 不应再通过修改全局变量实现，要直接传入 `run_phase2(..., prompt=custom_prompt)`
- `main.py` 后续只保留交互编辑 prompt 的外壳

验收：

- `batch/runner/phase_runner.py` 不再 import `main`
- `skill.py` 不再 import `main` 或临时修改 `main.PHASE2_PROMPT`
- `rg "from main|import main" sp_video` 不再命中生产路径

### P3：抽出 Phase3 / Phase4 包装层

目标：统一入口名称，先包装旧逻辑，不急着深拆 `make_time/` 和 `make_video/`。

新建：

| 文件 | 内容 |
|------|------|
| `phase3_match/runner.py` | 包装 `make_time.step2.get_keep_intervals`，返回过滤后的 valid intervals |
| `phase4_cut/runner.py` | 包装 `make_video.step3.cut_video_filter_complex`，支持显式 `output_path` |

建议函数签名：

```python
def get_keep_intervals(srt_path, script_text, output_path=None):
    ...

def keep_intervals_to_segments(keep_intervals):
    ...

def cut_video(mp4_path, output_path, keep_intervals=None, segments=None):
    ...
```

注意：

- 第一轮不要继续使用 `cut_video_main()` 作为新入口，因为它写死 `data/hanbing/{video_id}/output.mp4`
- `batch_generator.py` 当前依赖 `cut_video_main(intervals, mp4_path, video_id, "batch")`，应改为由调用方决定输出目录
- `make_time/`、`make_video/` 暂时保留，Phase3/4 只做稳定外壳

验收：

- `batch_generator.py` 不再直接 import `make_video.step3.cut_video_main`
- 新的 `phase4_cut.runner.cut_video` 能被 5min / short / batch 三种模式共用

### P4：迁入 sp_mini 单视频脚本

目标：把 `sp_mini` 的两个批处理入口搬进 `sp_video/scripts/`，并改为依赖 phase/shared。

新建：

| 新文件 | 来源 | 改动 |
|--------|------|------|
| `scripts/run_5min.py` | `sp_mini/scripts/run_single_video_5min_batch.py` | 改 import，使用 `PROMPT_5MIN` / `PROMPT_5MIN_EXPAND` |
| `scripts/run_short.py` | `sp_mini/scripts/run_single_video_short_batch.py` | 改 import，使用 `PROMPT_SHORT` |

保留行为：

- `run_5min.py` 保留 `ProgressTracker`
- `run_5min.py` 保留 `<220s` 触发 retry 的逻辑
- `run_short.py` 保持无 retry 的简单流程
- 两者继续输出 `summary.json`、`events.jsonl`、`step1.txt`、`step2.txt`、`intervals.json`

应消除的重复：

- `TeeStream`
- `ensure_dir`
- `make_run_id`
- `find_video_pairs`
- `keep_intervals_to_segments`
- `get_total_duration`
- `get_srt_duration_sec`
- `count_timeline_entries`
- `classify_duration_status`

验收：

- `python scripts/run_5min.py --help` 正常
- `python scripts/run_short.py --help` 正常
- 两个脚本不再 import `sp_mini` 或 `main`

### P5：切换 sp_video 现有入口

目标：让原 sp_video 主路径都走新 phase/shared。

修改：

| 文件 | 改动 |
|------|------|
| `batch/runner/phase_runner.py` | 改用 `phase1_select.runner`、`phase2_rewrite.runner`、`phase3_match.runner` |
| `batch_generator.py` | 改用 `phase4_cut.runner.cut_video` |
| `skill.py` | 改用 phase runner；自定义 prompt 通过参数传递 |
| `main.py` | 变成薄 CLI，内部调用 phase runner，或暂时作为兼容入口保留 |

验收：

- `rg "from main|import main" sp_video` 不命中生产代码
- `rg "cut_video_main" sp_video` 只允许在旧兼容层或测试说明里出现
- 原 `batch_generator.py` 的单视频 / 多视频流程仍可运行
- `skill.py start/phase2/generate` 的 JSON stdout 行为不变

### P6：清理旧代码与文档收口

目标：确认新路径稳定后再删除或降级旧入口。

清理策略：

1. `main.py` 如果外部仍有人手动使用，就保留为 CLI wrapper
2. `batch/logger.py` 可改成从 `shared.logger` re-export，避免断旧 import
3. `make_time/`、`make_video/` 第一轮不删除；等 Phase3/4 深拆时再处理
4. `sp_mini/` 暂时保留一段时间作为对照，确认线上流程完全迁入后再归档或删除

验收：

- 文档更新 README / ARCHITECTURE 中的新入口
- 所有新模块可 `compileall`
- 手动跑通三种模式各一次

---

## 第一轮不做的事

为了降低融合风险，第一轮明确不做这些：

1. 不重写 `make_time` 的匹配算法
2. 不重写 `make_video/filter_builder.py`
3. 不调整评分算法和多视频组合策略
4. 不改变 `settings.py` 的配置加载方式
5. 不立刻删除 `sp_mini/`
6. 不把所有脚本强行改成一个超级入口

这些可以作为第二轮重构：

- 深拆 `make_time/` 到 `phase3_match/srt_parser.py`、`script_parser.py`、`matcher.py`
- 深拆 `make_video/` 到 `phase4_cut/filter_builder.py`、`runner.py`
- 建立正式 `modes.py`
- 为 phase runner 增加 mock LLM 测试

---

## 最小可交付版本（MVP）

最小可交付不是“目录都完美”，而是以下条件同时成立：

1. `sp_video` 内可以运行 `scripts/run_5min.py`
2. `sp_video` 内可以运行 `scripts/run_short.py`
3. 原 `batch_generator.py` 仍能运行
4. `skill.py` 不再依赖 `main.py`
5. `main.py` 即使保留，也只是 CLI wrapper，不再是业务函数仓库
6. Phase1/2 prompt 全部集中在 `phase1_select/prompts.py` 和 `phase2_rewrite/prompts.py`
7. 新增代码不改变 Phase3 匹配和 Phase4 裁剪算法

---

## 手动验收清单

每完成一个大阶段后至少检查：

```bash
python -m compileall shared phase1_select phase2_rewrite phase3_match phase4_cut scripts
python scripts/run_5min.py --help
python scripts/run_short.py --help
python batch_generator.py --help
python skill.py list
```

有测试环境和素材时再跑：

```bash
python scripts/run_5min.py --input_dir data/video --force
python scripts/run_short.py --input_dir data/video --force
python batch_generator.py
```

验收输出重点：

- `step1.txt` / `step2.txt` / `intervals.json` 正常生成
- `summary.json` 字段和旧版本兼容
- `events.jsonl` 能记录 phase 成功/失败
- 5min 模式仍会输出 heartbeat 和 retry 相关日志
- batch 模式仍会生成候选、评分并输出最终视频
