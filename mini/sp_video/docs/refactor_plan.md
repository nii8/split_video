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
│   │
│   ├── phase_runner.py                # [执行层] 批量跑Phase1/2/3，生成候选池
│   │
│   ├── evaluator.py                   # [评分层] 基础机器评分（时长/完整度）
│   ├── transition_scorer.py           # [评分层] 转场规则评分（片段碎/跳跃）
│   ├── visual_scorer.py               # [评分层] 视觉LLM评分（多模态看画面）
│   ├── frame_sampler.py               # [评分层] 从mp4抽帧（供visual_scorer用）
│   ├── image_grid.py                  # [评分层] 把帧拼成9宫格（供visual_scorer用）
│   │
│   ├── multi_video_selector.py        # [多视频组合层] 构建多视频输入结构
│   ├── video_pool_builder.py          # [多视频组合层] 构建单视频候选片段池
│   ├── video_combiner.py              # [多视频组合层] 主+副视频组合成候选
│   ├── multi_video_scorer.py          # [多视频组合层] 给多视频组合评分
│   │
│   └── visual_debug.py                # [调试层] 视觉评分过程可视化报告
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
[评分] batch/evaluator.py + transition_scorer.py + visual_scorer.py（可选）
    → 每个candidate得分
    ↓
[选优/组合] batch/video_combiner.py
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

### 修改 import 的文件

| 文件 | 改动 |
|------|------|
| `batch/phase_runner.py` | 不再 import main.py，改从 phase1_select/runner, phase2_rewrite/runner, shared/llm_caller |
| `batch_generator.py` | 改从新的 phase 模块 import |
| `skill.py` | 改从新的 phase 模块 import |

### 删除文件

| 文件 | 原因 |
|------|------|
| `main.py` | 职责全部分散到各 phase 目录和 shared/ |

### 暂时保留不动

- `make_time/`：phase3_match/runner.py 内部调用它，待后续整理
- `make_video/`：phase4_cut/runner.py 内部调用它，待后续整理
- `batch/` 下所有文件：只改 import，逻辑不动

---

## Import 路径变化示例

```python
# 改之前（batch/phase_runner.py）
from main import run_phase1_batch, run_phase2_batch
from make_time.step2 import get_keep_intervals

# 改之后
from phase1_select.runner import run_phase1
from phase2_rewrite.runner import run_phase2
from phase3_match.runner import get_keep_intervals
from shared.llm_caller import call_llm_batch

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
7. 更新 `batch/phase_runner.py`、`batch_generator.py`、`skill.py` 的 import
8. 删除 `main.py`
9. 验证：跑 scripts/run_5min.py 和 batch_generator.py

---

## 注意事项

1. **settings.py 各自独立**：sp_mini 和 sp_video 的配置不同，只保留 sp_video 的 settings.py
2. **call_llm_batch 函数差异**：sp_mini 的版本有 heartbeat_callback 参数，sp_video 的没有 → shared/llm_caller.py 采用 sp_mini 版本（含 heartbeat_callback，向下兼容）
3. **运行路径**：在 sp_video/ 目录下运行，`PYTHONPATH=.` 或直接 python -m 方式执行
