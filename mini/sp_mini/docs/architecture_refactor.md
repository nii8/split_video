# sp_mini 架构重构方案

## 背景

当前代码存在以下问题：
1. `main.py` 职责混乱，既是 CLI 入口，又被 scripts/ 当工具库 import（倒置依赖）
2. 两个批处理脚本（5min / short）大量重复代码（约100行）
3. `make_time/`、`make_video/` 目录名不反映语义，`step2`、`step3`、`mode2` 是历史遗留名字
4. Phase3 的逻辑分散在5个文件，阅读需要频繁跳转
5. 两套版本的 prompt 分别藏在 `main.py` 和 `run_single_video_short_batch.py` 里

## 核心设计原则

**代码结构直接映射到处理流程。哪个 phase 出问题，去对应的 phase 文件夹。**

---

## 数据流程（不变）

```
输入: video.srt + video.mp4
         ↓
    [Phase1] LLM读SRT → 筛选候选字幕文本（step1.txt）
         ↓
    [Phase2] LLM读候选 → 重组成脚本文本（step2.txt）
         ↓
    [Phase3] 脚本文本 + SRT → AI匹配 → 时间轴列表（intervals.json）
         ↓
    [Phase4] intervals + video.mp4 → ffmpeg → 输出.mp4
```

---

## 目标目录结构

```
sp_mini/
│
├── settings.py              # 全局配置（不变）
│
├── phase1_select/           # Phase1: SRT → 候选字幕文本
│   ├── __init__.py
│   ├── prompts.py           # PROMPT_5MIN, PROMPT_SHORT（两套prompt放在一起便于对比）
│   └── runner.py            # run_phase1(srt_path, prompt) → str
│
├── phase2_rewrite/          # Phase2: 候选文本 → 重组脚本
│   ├── __init__.py
│   ├── prompts.py           # PROMPT_5MIN, PROMPT_5MIN_EXPAND, PROMPT_SHORT
│   └── runner.py            # run_phase2(phase1_text, prompt) → str
│
├── phase3_match/            # Phase3: 脚本文本+SRT → 时间轴intervals
│   ├── __init__.py
│   ├── prompts.py           # build_match_subtitle_prompt, build_find_subtitle_prompt, build_check_similarity_prompt
│   ├── srt_parser.py        # parse_srt_file(srt_path) → zimu_list
│   ├── script_parser.py     # parse_script(script_text) → yuanwen_list（原 mode2.get_yuanwen_mode2）
│   ├── matcher.py           # AI匹配核心：call_ai_match, find_intervals_by_ai, merge_intervals
│   └── runner.py            # get_keep_intervals(srt_path, script_text) → intervals（顶层入口）
│
├── phase4_cut/              # Phase4: intervals+mp4 → 输出视频
│   ├── __init__.py
│   ├── filter_builder.py    # build_filter_complex(segments) → str（内容不变）
│   └── runner.py            # cut_video(mp4_path, output_path, segments)
│
├── shared/                  # 公共工具（不属于任何phase）
│   ├── __init__.py
│   ├── llm_client.py        # OpenAI客户端工厂：make_client(mod) → client, model_name
│   ├── llm_caller.py        # call_llm_batch(prompt, heartbeat_cb) → str
│                            # call_llm_stream(prompt) → str
│   ├── logger.py            # BatchLogger（内容不变，从 batch/logger.py 迁入）
│   ├── output.py            # info/warn/error/debug（内容不变，从 batch/output.py 迁入）
│   └── utils.py             # 批处理公共工具函数（从两个脚本中提取）：
│                            #   TeeStream, make_run_id, ensure_dir,
│                            #   find_video_pairs, keep_intervals_to_segments,
│                            #   get_total_duration, get_srt_duration_sec,
│                            #   count_timeline_entries, classify_duration_status,
│                            #   snapshot_prompts
│
└── scripts/                 # 入口：串联4个phase
    ├── run_5min.py          # 5分钟版批处理（含 ProgressTracker + retry 逻辑）
    └── run_short.py         # 短精华版批处理（更简洁，无retry）
```

---

## 各文件夹职责说明

### phase1_select/
- **职责**：负责"用什么prompt让LLM从SRT里筛选候选字幕"
- **改prompt**：改 `prompts.py`
- **调LLM失败**：看 `runner.py`
- `runner.py` 只调用 `shared/llm_caller.py`，不自己创建client

### phase2_rewrite/
- **职责**：负责"用什么prompt让LLM把候选字幕重组成脚本"
- **两套版本差异**：5min版和short版的prompt都在 `prompts.py` 里，一目了然
- `PROMPT_5MIN_EXPAND` 是5min版触发retry时使用的扩充prompt

### phase3_match/
- **职责**：负责"把LLM输出的脚本文本，精确匹配回SRT时间轴"
- **子文件职责**：
  - `srt_parser.py`：只负责读 .srt 文件并解析成 zimu_list（替代 make_time/step2.py 中的解析部分）
  - `script_parser.py`：只负责解析LLM输出的脚本文本为 yuanwen_list（替代 mode2.get_yuanwen_mode2）
  - `matcher.py`：核心匹配逻辑，含两阶段AI匹配、相似度验证、区间合并（整合 ai_caller.py + interval.py）
  - `prompts.py`：匹配和验证用的3个prompt（从 make_time/prompts.py 迁入）
  - `runner.py`：总入口，串联以上模块（替代 make_time/step2.py 的 get_keep_intervals）

### phase4_cut/
- **职责**：负责"用ffmpeg把时间轴裁切成视频"
- **ffmpeg命令问题**：看 `filter_builder.py`
- **ffmpeg执行问题**：看 `runner.py`
- 删除旧的 `cut_video_main()` 接口（写死输出到 data/hanbing/ 的旧接口，当前批处理已不使用）

### shared/
- **职责**：不属于任何特定phase的横切工具
- `llm_client.py`：统一管理LLM客户端创建（qwen/deepseek路由），替代 make_time/chat.py
- `llm_caller.py`：统一管理LLM调用方式（batch/stream），替代 main.py 中的调用函数
- `logger.py`：结构化日志，内容不变
- `output.py`：终端打印，内容不变
- `utils.py`：从两个批处理脚本中提取的重复工具函数，只维护一份

### scripts/
- **职责**：串联4个phase的主流程，处理批处理逻辑、日志归档、错误处理
- `run_5min.py` 还负责：ProgressTracker进度跟踪、retry机制（首轮<220s触发扩充重试）
- `run_short.py` 相对简洁，无retry

---

## 旧文件与新文件的对应关系

| 旧文件 | 迁移到 | 说明 |
|--------|--------|------|
| `main.py` 中的 PHASE1_PROMPT | `phase1_select/prompts.py` | |
| `main.py` 中的 PHASE2_PROMPT | `phase2_rewrite/prompts.py` | |
| `main.py` 中的 call_llm_batch/stream | `shared/llm_caller.py` | |
| `main.py` 中的 run_phase1_batch/run_phase2_batch | `phase1_select/runner.py`, `phase2_rewrite/runner.py` | |
| `make_time/chat.py` | `shared/llm_client.py` | 去掉无用的 ask_dic 全局变量 |
| `make_time/prompts.py` | `phase3_match/prompts.py` | 内容不变，只移位置 |
| `make_time/step2.py` | `phase3_match/runner.py` + `phase3_match/srt_parser.py` | |
| `make_time/mode2.py` 解析部分 | `phase3_match/script_parser.py` | get_yuanwen_mode2 |
| `make_time/mode2.py` 匹配部分 | `phase3_match/matcher.py` | |
| `make_time/ai_caller.py` | `phase3_match/matcher.py` | 合并进matcher |
| `make_time/interval.py` | `phase3_match/matcher.py` | 合并进matcher |
| `make_time/time_utils.py` | `phase3_match/srt_parser.py` | 合并进srt_parser |
| `make_video/filter_builder.py` | `phase4_cut/filter_builder.py` | 内容不变，只移位置 |
| `make_video/step3.py` | `phase4_cut/runner.py` | 删除旧的 cut_video_main 接口 |
| `batch/logger.py` | `shared/logger.py` | 内容不变，只移位置 |
| `batch/output.py` | `shared/output.py` | 内容不变，只移位置 |
| 两个脚本里重复的工具函数 | `shared/utils.py` | TeeStream等约100行公共代码 |
| `scripts/run_single_video_5min_batch.py` | `scripts/run_5min.py` | 改名更简洁 |
| `scripts/run_single_video_short_batch.py` | `scripts/run_short.py` | 改名更简洁 |
| `main.py` CLI入口部分 | 可保留为 `main.py` 或删除 | 交互模式用，当前批处理不依赖 |

---

## 两套版本（5min vs short）的差异

**差异只在 Phase1 和 Phase2 的 prompt**，Phase3、Phase4 完全共用。

```python
# scripts/run_5min.py
from phase1_select.prompts import PROMPT_5MIN
from phase2_rewrite.prompts import PROMPT_5MIN, PROMPT_5MIN_EXPAND

# scripts/run_short.py
from phase1_select.prompts import PROMPT_SHORT
from phase2_rewrite.prompts import PROMPT_SHORT
```

---

## 实施建议

### 实施顺序（风险从低到高）

1. **第一步**：创建 `shared/utils.py`，把两个脚本中重复的工具函数提取进来（纯搬移，不改逻辑）
2. **第二步**：创建 `shared/llm_client.py` 和 `shared/llm_caller.py`，把 chat.py 和 main.py 的LLM调用搬进来
3. **第三步**：创建 `phase1_select/` 和 `phase2_rewrite/`，把 prompt 和 runner 搬进来，解开 scripts → main.py 的倒置依赖
4. **第四步**：创建 `phase3_match/`，把 make_time/ 下的文件按职责重新组织
5. **第五步**：创建 `phase4_cut/`，把 make_video/ 搬进来
6. **第六步**：更新 `scripts/run_5min.py` 和 `scripts/run_short.py` 的 import，验证功能正常
7. **第七步**：删除旧目录（`make_time/`、`make_video/`、`batch/`）和旧文件（`main.py` 的工具部分）

### 每一步完成后验证

- 在 `data/video/` 下放1个视频+字幕，跑一次批处理，确认输出正常
- 检查 `events.jsonl` 和 `run_summary.json` 结构完整

### 注意事项

- `make_time/time_utils.py` 中的 `is_start_bigger_end` 使用 datetime 比较时间，要注意迁移时不要丢失
- `mode2.py` 中对 `...` 和 `……` 的特殊处理逻辑要完整迁移到 `script_parser.py`
- `merge_intervals` 中对 `zimu_mode` 的 `[[mode=N]]` 标注是调试信息，迁移时保留
- `settings.py` 中的 `OUTPUT_DEBUG_ENABLED` 控制 debug 输出，`shared/output.py` 需要继续 import settings
