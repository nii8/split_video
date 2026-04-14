# 视频质量评分系统设计方案

## 概述

当前项目数据流：
```
SRT字幕 → Phase1筛选 → Phase2脚本 → Phase3时间轴intervals → Phase4评分 → Phase5生成视频
```

## 多维度评分体系

```
总分 = Σ(维度分 × 权重)

┌─────────────────────────────────────────────────────────────────────┐
│  维度1: 内容质量 (30%)  - 叙事完整性、情感起伏、钩子强度              │
│  维度2: 节奏控制 (25%)  - 片段时长分布、转场密度、黄金3秒             │
│  维度3: 时间覆盖 (20%)  - 原视频利用率、片段连续性                    │
│  维度4: 技术指标 (15%)  - 画面稳定性、音画同步                       │
│  维度5: 去重惩罚 (10%)  - 内容重复度检测                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 维度1: 内容质量评分 (0-10分)

基于脚本内容的质量评分，数据来源: Phase2输出的脚本 + intervals中的文本

```python
def score_content_quality(script_content: str, intervals: list) -> float:
    """
    基于脚本内容的质量评分
    数据来源: Phase2输出的脚本 + intervals中的文本
    """
    scores = {}
    
    # 1.1 钩子强度 (0-2.5分)
    # 检查前3秒/前5秒是否有高冲击力句子
    first_intervals = [i for i in intervals if parse_time(i[0][0]) < 5.0]
    hook_score = analyze_hook_strength(first_intervals)  # 可用LLM或关键词匹配
    
    # 1.2 叙事完整性 (0-2.5分)
    # 开头有钩子、中间有冲突/转折、结尾有升华/互动
    narrative_score = check_narrative_structure(script_content)
    
    # 1.3 情感起伏 (0-2.5分)
    # 分析文本情感变化曲线，避免单调
    emotion_variance = calculate_emotion_variance(intervals)
    
    # 1.4 信息密度 (0-2.5分)
    # 每秒有效信息量，避免拖沓
    total_duration = sum(parse_time(i[0][1]) - parse_time(i[0][0]) for i in intervals)
    info_density = len(extract_keywords(script_content)) / max(total_duration, 1)
    
    return hook_score + narrative_score + emotion_score + density_score
```

---

## 维度2: 节奏控制评分 (0-10分)

基于时间片段的节奏评分，数据来源: Phase3输出的intervals

```python
def score_pacing(intervals: list, video_duration: float) -> float:
    """
    基于时间片段的节奏评分
    数据来源: Phase3输出的intervals
    """
    durations = [parse_time(i[0][1]) - parse_time(i[0][0]) for i in intervals]
    
    # 2.1 片段时长分布 (0-3分)
    # 理想: 大部分片段在3-8秒，标准差适中
    avg_duration = sum(durations) / len(durations)
    std_dev = statistics.stdev(durations) if len(durations) > 1 else 0
    duration_score = score_duration_distribution(avg_duration, std_dev)
    
    # 2.2 转场密度 (0-3分)
    # 每分钟转场次数，抖音建议 10-20次/分钟
    total_duration = sum(durations)
    transitions_per_min = (len(intervals) - 1) / (total_duration / 60)
    transition_score = score_transitions(transitions_per_min)
    
    # 2.3 黄金3秒 (0-2分)
    # 第一个片段是否足够吸引人（时长适中、内容有力）
    first_duration = durations[0] if durations else 0
    golden_3s_score = 2.0 if 2.0 <= first_duration <= 5.0 else 1.0
    
    # 2.4 结尾节奏 (0-2分)
    # 最后片段是否留有余味或互动引导
    last_duration = durations[-1] if durations else 0
    ending_score = 2.0 if 3.0 <= last_duration <= 8.0 else 1.0
    
    return duration_score + transition_score + golden_3s_score + ending_score
```

---

## 维度3: 时间覆盖评分 (0-10分)

评估对原视频的利用效率，数据来源: intervals + 原SRT文件 + 视频时长

```python
def score_time_coverage(intervals: list, srt_path: str, video_duration: float) -> float:
    """
    评估对原视频的利用效率
    数据来源: intervals + 原SRT文件 + 视频时长
    """
    # 3.1 视频覆盖率 (0-4分)
    # 选中片段总时长 / 原视频时长
    selected_duration = sum(parse_time(i[0][1]) - parse_time(i[0][0]) for i in intervals)
    coverage = selected_duration / video_duration
    coverage_score = min(4.0, coverage * 8)  # 50%覆盖率=4分
    
    # 3.2 时间轴连续性 (0-3分)
    # 选中片段是否过于分散
    gaps = calculate_gaps(intervals)
    continuity_score = score_continuity(gaps, video_duration)
    
    # 3.3 有效片段比例 (0-3分)
    # 去除无效/空白片段后的有效比例
    valid_ratio = len([i for i in intervals if i[0][0] and i[1]]) / len(intervals)
    valid_score = valid_ratio * 3.0
    
    return coverage_score + continuity_score + valid_score
```

---

## 维度4: 技术指标评分 (0-10分)

需要实际分析视频文件，数据来源: 视频文件 + FFmpeg/FFprobe

```python
def score_technical(video_path: str, intervals: list) -> float:
    """
    需要实际分析视频文件
    数据来源: 视频文件 + FFmpeg/FFprobe
    """
    # 4.1 画面稳定性 (0-4分)
    # 检查切点是否在场景切换/关键帧位置
    cut_points = [i[0][0] for i in intervals]
    scene_score = check_scene_boundaries(video_path, cut_points)
    
    # 4.2 音画同步 (0-3分)
    # 切点是否在静音/自然断句处
    audio_score = check_audio_continuity(video_path, intervals)
    
    # 4.3 分辨率一致性 (0-3分)
    # 所选片段分辨率是否一致
    resolution_score = check_resolution_consistency(video_path, intervals)
    
    return scene_score + audio_score + resolution_score
```

---

## 维度5: 去重与惩罚 (-5 到 0分)

检测内容重复，数据来源: intervals中的文本

```python
def score_dedup_penalty(intervals: list) -> float:
    """
    检测内容重复
    数据来源: intervals中的文本
    """
    texts = [i[1] for i in intervals]
    
    # 5.1 文本重复检测
    similarity_matrix = calculate_text_similarity(texts)
    duplicate_ratio = count_high_similarity_pairs(similarity_matrix)
    
    # 5.2 时间重叠检测
    time_overlaps = check_time_overlaps(intervals)
    
    # 惩罚: 重复度越高，扣分越多
    penalty = 0
    if duplicate_ratio > 0.3:
        penalty -= 3.0
    elif duplicate_ratio > 0.2:
        penalty -= 2.0
    elif duplicate_ratio > 0.1:
        penalty -= 1.0
    
    if time_overlaps > 0:
        penalty -= min(2.0, time_overlaps * 0.5)
    
    return penalty
```

---

## 分阶段实现策略

```
┌──────────────────────────────────────────────────────────────────────┐
│  阶段1 (当前可快速实现):                                               │
│    - 节奏控制评分 (仅依赖intervals)                                    │
│    - 时间覆盖评分 (intervals + SRT)                                   │
│    - 去重惩罚 (intervals文本)                                         │
│                                                                       │
│  阶段2 (中等复杂度):                                                   │
│    - 内容质量评分 (调用LLM分析脚本)                                    │
│    - 需要额外的LLM调用，但可复用现有API                                │
│                                                                       │
│  阶段3 (需要视频处理):                                                 │
│    - 技术指标评分 (FFprobe分析视频)                                    │
│    - 场景边界检测、音频连续性分析                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 简化版立即可用方案

当前可实现的评分（无需额外依赖）：

```python
def evaluate_quality(video_path: str, intervals: list, srt_path: str = None) -> dict:
    """
    当前可实现的评分（无需额外依赖）
    """
    import statistics
    
    if not intervals:
        return {"total": 0, "error": "无有效片段"}
    
    durations = [parse_time_s(i[0][1]) - parse_time_s(i[0][0]) for i in intervals]
    total_duration = sum(durations)
    
    # 1. 片段数量评分 (0-3分): 5-15个片段最优
    count = len(intervals)
    count_score = 3.0 if 5 <= count <= 15 else max(0, 3.0 - abs(count - 10) * 0.3)
    
    # 2. 时长分布评分 (0-3分): 平均3-6秒，标准差适中
    avg_duration = total_duration / count
    std_dev = statistics.stdev(durations) if count > 1 else 0
    duration_score = 3.0 if 3 <= avg_duration <= 6 and std_dev < 3 else max(0, 2.0 - std_dev * 0.5)
    
    # 3. 去重评分 (0-2分)
    texts = [str(i[1]) for i in intervals]
    unique_ratio = len(set(texts)) / len(texts) if texts else 0
    dedup_score = unique_ratio * 2.0
    
    # 4. 转场密度评分 (0-2分): 每分钟8-15次转场
    transitions_per_min = (count - 1) / (total_duration / 60) if total_duration > 0 else 0
    transition_score = 2.0 if 8 <= transitions_per_min <= 15 else max(0, 2.0 - abs(transitions_per_min - 11) * 0.2)
    
    total = round(count_score + duration_score + dedup_score + transition_score, 2)
    
    return {
        "count": round(count_score, 2),
        "duration": round(duration_score, 2),
        "dedup": round(dedup_score, 2),
        "transition": round(transition_score, 2),
        "total": total
    }

def parse_time_s(time_str: str) -> float:
    """将 SRT 时间格式转为秒"""
    h, m, s_ms = time_str.split(":")
    s, ms = s_ms.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
```

---

## 参考指标

### 抖音爆款视频特征

| 指标 | 理想范围 | 说明 |
|------|----------|------|
| 视频时长 | 15-60秒 | 完播率最优区间 |
| 片段数量 | 5-15个 | 节奏感适中 |
| 平均片段时长 | 3-6秒 | 信息密度适中 |
| 转场频率 | 8-15次/分钟 | 节奏感强 |
| 开头3秒 | 必须有钩子 | 决定完播率 |
| 结尾 | 升华/互动 | 提升互动率 |

### 评分阈值建议

| 总分 | 等级 | 处理建议 |
|------|------|----------|
| 8-10 | 优秀 | 直接生成 |
| 7-8 | 良好 | 可生成 |
| 5-7 | 一般 | 建议重试 |
| < 5 | 较差 | 需重新筛选 |