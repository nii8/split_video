# 多视频最小闭环任务规划 v0

> 目标：实现"最小多视频闭环（仅候选，不输出视频）"
>
> 边界决策：选择**方案 A**（闭到候选 + summary，不生成实际视频文件）。
> 原因：风险低、容易验证方向是否正确，避免 `cut_video_main()` 的多路 mp4 拼接问题。

---

## 背景与断点分析

当前 `process_multi_video()` 已经有完整骨架，但链路存在两处核心断点：

**断点 1（数据结构不对齐）**：`video_pool_builder.py` 的 `build_video_segment_pool()` 接受
`intervals_list`，格式是 `[[{start, end, text}, ...], ...]`（字典列表的列表）。
但 `batch_generator.py` 里 `process_multi_video()` 传给它的是 `phase3_results` 拆出来的
`intervals`，而 Phase3 实际产出的 `keep_intervals` 格式是
`[[(start_str, end_str), text], ...]`（元组 + SRT 时间字符串）。
两种格式直接相撞，当前没有任何转换层。

**断点 2（Phase3 复用逻辑错误）**：`process_multi_video()` 在调用
`run_phase3_loop(video_id, srt_path, [], phase3_dir, logger)` 时，
第三个参数 `phase2_files=[]`，导致 Phase3 无输入直接失败，
候选片段永远为空。正确做法应先运行 Phase1/Phase2，再运行 Phase3。

**本次任务目标**：修通这两个断点，让多视频候选能真正产生，并写出 summary.json，不生成实际视频文件。

---

## 任务列表

---

### Task 1：实现 `keep_intervals_to_segments(video_id, keep_intervals)` 转换函数

**文件**：`batch/video_pool_builder.py`（在已有函数后追加，不改动现有函数签名）

**职责**：把单视频 Phase3 输出的 `keep_intervals` 转成片段池所需的 `segments` 列表。

---

#### 输入

```python
video_id = "A001"

keep_intervals = [
    [("00:00:10,000", "00:00:20,000"), "第一段文本"],
    [("00:00:30,000", "00:00:45,000"), "第二段文本"],
    [(None, None), "未匹配段"],          # 无效片段，必须跳过
]
```

`keep_intervals` 格式定义（来自 `make_time/step2.py`）：
- 每个元素是 `[(start_str, end_str), text]`
- `start_str` / `end_str` 是 SRT 时间格式：`"HH:MM:SS,mmm"`
- 未匹配的片段为 `(None, None)`，必须跳过

---

#### 输出

```python
[
    {
        "video_id": "A001",
        "start": 10.0,      # float，单位秒
        "end": 20.0,        # float，单位秒
        "text": "第一段文本",
    },
    {
        "video_id": "A001",
        "start": 30.0,
        "end": 45.0,
        "text": "第二段文本",
    },
    # (None, None) 的片段被跳过，不出现在输出中
]
```

---

#### 函数签名

```python
def keep_intervals_to_segments(video_id: str, keep_intervals: list) -> list:
```

---

#### SRT 时间字符串转秒的子逻辑

输入 `"00:01:23,456"`，输出 `83.456`（float）。

格式规则：`HH:MM:SS,mmm`，其中逗号分隔毫秒。

---

#### 禁止项

- **禁止**修改 `build_video_segment_pool()` 的签名
- **禁止**修改 `build_multi_video_pools()` 的签名
- **禁止**在这个函数里调用任何 LLM、ffmpeg、文件 I/O
- **禁止**在函数内部 print 任何日志（调用方负责日志）
- **禁止**处理非 SRT 格式的时间字符串（其他格式不是这个函数的职责）

---

### Task 2：实现 `run_single_video_phases(video_id, srt_path, mp4_path, logger)` 函数

**文件**：`batch_generator.py`（在 `process_multi_video()` 函数前追加）

**职责**：为单个视频跑完 Phase1 → Phase2 → Phase3，返回标准化的 segments 列表和基础评分列表，供多视频池构建使用。这个函数是对 `process_video()` 里 Phase1-4 逻辑的**提取和简化版**，专供多视频流程调用。

---

#### 输入

```python
video_id = "A001"
srt_path  = "/data/hanbing/A001/A001.srt"
mp4_path  = "/data/hanbing/A001/A001.mp4"
logger    = BatchLogger(...)
```

---

#### 输出

成功时：

```python
{
    "video_id": "A001",
    "segments": [
        {"video_id": "A001", "start": 10.0, "end": 20.0, "text": "...", "base_score": 7.5},
        {"video_id": "A001", "start": 30.0, "end": 45.0, "text": "...", "base_score": 8.0},
    ]
}
```

失败时（Phase1/2/3 任意阶段为空）：

```python
None
```

---

#### 函数签名

```python
def run_single_video_phases(video_id, srt_path, mp4_path, logger):
```

---

#### 内部逻辑说明

1. 调用 `run_phase1_loop()` → 得到 `phase1_files`，若空则返回 `None`
2. 调用 `run_phase2_loop()` → 得到 `phase2_files`，若空则返回 `None`
3. 调用 `run_phase3_loop()` → 得到 `phase3_results`（`[(idx, keep_intervals), ...]`），若空则返回 `None`
4. 对每个 `keep_intervals` 调用 `keep_intervals_to_segments(video_id, keep_intervals)`（Task 1 实现）
5. 对每个 `keep_intervals` 调用 `evaluate_quality(mp4_path, keep_intervals)` 取 `total` 分
6. 将 `base_score` 写入对应 segment 的 `base_score` 字段
7. 汇总所有 segments 返回

---

#### 禁止项

- **禁止**在这个函数里调用 `cut_video_main()`（不生成视频）
- **禁止**写任何输出文件到磁盘（日志和 phase 中间结果由各 runner 自己负责）
- **禁止**修改 `run_phase1_loop` / `run_phase2_loop` / `run_phase3_loop` 的签名
- **禁止**修改 `process_video()` 的逻辑（单视频主链路不动）
- **禁止**在 segments 里放 `keep_intervals` 原始格式（必须是 Task 1 转换后的 float 秒格式）

---

### Task 3：重写 `process_multi_video()` 的候选生成段 + 输出 summary.json

**文件**：`batch_generator.py`（只改 `process_multi_video()` 函数体，不改函数签名）

**职责**：修通多视频候选生成主链路，去掉当前的断点逻辑，改用 Task 2 的 `run_single_video_phases()`，最终写出 summary.json，不调用 `cut_video_main()`。

---

#### 输入（函数签名不变）

```python
def process_multi_video(videos_data, logger):
    # videos_data: [(video_id, srt_path, mp4_path), ...]
```

---

#### 期望的主链路流程

```
for each (video_id, srt_path, mp4_path) in videos_data:
    result = run_single_video_phases(video_id, srt_path, mp4_path, logger)
    若 result 为 None 则跳过该视频

pools = build_multi_video_pools_from_segments(per_video_results)
    → 内部直接用 segments 列表构建，不经过 keep_intervals_to_segments（已在 Task2 转换好）

candidates = build_multi_video_candidates(pools, max_candidates=20)

scored_candidates = []
for candidate in candidates:
    mv_result = score_multi_video_candidate(candidate)
    base_score = 取 candidate["segments"] 中第一个有 base_score 的值，默认 7.5
    merged = merge_multi_video_score({"total": base_score, "base_total": base_score}, mv_result)
    scored_candidates.append({"candidate": candidate, "score": merged})

按 score["total"] 降序排列

写出 summary.json 到 data/batch_results/multi_video/summary.json
```

---

#### summary.json 输出格式

```json
{
  "total_candidates": 15,
  "top_candidates": [
    {
      "candidate_id": "C001",
      "total_score": 8.2,
      "base_total": 7.5,
      "multi_video_score": 9.5,
      "segment_count": 3,
      "video_ids": ["A001", "B002"],
      "segments": [
        {"video_id": "A001", "start": 10.0, "end": 20.0, "text": "..."},
        {"video_id": "B002", "start": 5.0,  "end": 15.0, "text": "..."}
      ]
    }
  ],
  "source_videos": ["A001", "B002"]
}
```

`top_candidates` 只保留前 5 个（降序）。

---

#### 关于 `build_multi_video_pools` 的适配

当前 `build_multi_video_pools()` 接受的是 `interval_candidates_map`（Phase3 原始格式），与 Task 2 输出的 segments 不兼容。

解决方案：**不改 `build_multi_video_pools()`**，而是在 Task 3 里构建一个临时的 `pools` 字典，直接用 Task 2 返回的 segments 数据：

```python
pools = {}
for result in per_video_results:
    video_id = result["video_id"]
    pools[video_id] = {
        "video_id": video_id,
        "segments": result["segments"],
        "total_segments": len(result["segments"]),
    }
```

这样绕开格式不对齐问题，直接喂给 `build_multi_video_candidates(pools)`。

---

#### 禁止项

- **禁止**在 `process_multi_video()` 内调用 `cut_video_main()`（本次目标是仅候选，不生成视频）
- **禁止**删除 `process_multi_video()` 后面原有的视频生成代码（注释掉即可，保留结构）
- **禁止**修改 `process_video()`（单视频主链路不动）
- **禁止**修改 `main()` 函数的入口判断逻辑
- **禁止**在不同视频之间共享 Phase1/Phase2 的中间文件（每个视频独立走自己的 phase 目录）
- **禁止**在这个函数里直接 parse SRT 时间字符串（应由 Task 1 的函数负责）

---

## 验收标准

三个 Task 完成后，以下链路必须跑通：

1. `python batch_generator.py` 在 `BATCH_MULTI_VIDEO_ENABLE=True` 且有 ≥ 2 个视频时，进入多视频流程
2. 每个视频走完 Phase1 → Phase2 → Phase3，产生有效 segments
3. `build_multi_video_candidates()` 返回非空候选列表
4. `data/batch_results/multi_video/summary.json` 被写出，内容包含 `top_candidates`
5. **全程不调用 ffmpeg，不生成任何 .mp4 文件**

---

## 不做的事（本次 v0 边界）

- 不实现视觉评分（`visual_scorer`）的多视频扩展
- 不实现拼接自然度（`transition_scorer`）的多视频扩展
- 不实现跨视频视频文件的实际输出（`cut_video_main` 多路版）
- 不修改 `video_pool_builder.py` 中现有函数
- 不修改 `video_combiner.py` 的组合逻辑
- 不修改 `multi_video_scorer.py` 的评分逻辑
- 不改任何单视频主链路（`process_video` 保持完整）
