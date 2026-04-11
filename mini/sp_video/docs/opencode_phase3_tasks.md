# Opencode Phase3 Tasks

## 第三阶段目标

第三阶段只做最小版：

- 多视频输入
- 单视频片段池
- 最简单双视频组合
- 最简单兼容评分
- 接回总分体系

不要扩成功能大系统。

---

## Task 1: 多视频输入结构

### 目标

定义第三阶段最简单输入结构。

### 建议文件

- 新建：`batch/multi_video_selector.py`

### 建议内容

先支持这种输入：

```python
video_sources = [
    {"video_id": "A001", "video_path": "...", "srt_path": "..."},
    {"video_id": "B002", "video_path": "...", "srt_path": "..."},
]
```

### 不要做

- 不要一开始支持任意复杂嵌套结构
- 不要一开始做 class

### 验收标准

- 文件存在
- 有一个主入口函数
- 一眼能看懂输入长什么样

---

## Task 2: 单视频片段池

### 目标

给每个视频准备自己的候选片段池。

### 建议函数

- `build_video_segment_pool(video_id, intervals_list)`
- `build_multi_video_pools(video_sources, interval_candidates_map)`

### 最小思路

每个池先存：

- `video_id`
- `segments`
- `score`

每个 `segment` 最简单只要：

- `video_id`
- `start`
- `end`
- `text`
- `base_score`

### 不要做

- 不要一开始加太多字段
- 不要把视觉、多模态、复杂结构全揉进去

### 验收标准

- 每个视频都能形成一个列表
- 后面能从这个列表里拿片段

---

## Task 3: 最简单双视频组合

### 目标

只支持最简单的双视频组合。

### 建议函数

- `build_two_video_candidate(pool1, pool2)`
- `build_multi_video_candidates(pools)`

### 最小规则

先只允许：

- 主视频 2 段
- 副视频 1 段

或：

- 主视频 1 段
- 副视频 1 段

组合数不要太多。

### 不要做

- 不要允许任意多段自由组合
- 不要做复杂搜索

### 验收标准

- 能生成若干条“组合候选”
- 每条候选都能看出来自哪个视频、哪些时间段

---

## Task 4: 最简单兼容评分

### 目标

给多视频组合一个基础兼容评分。

### 建议函数

- `score_multi_video_candidate(candidate)`
- `merge_multi_video_score(score, multi_video_result)`

### 最小评分维度

只看：

- 片段数量是否过多
- 是否跨视频切太多次
- 总长度是否太长
- 文本主题是否明显跑偏

### 不要做

- 不要做复杂多模态跨视频比较
- 不要做很重的主题理解

### 验收标准

- 每个组合候选能得到一个基础分
- 基础分能并回 `total`

---

## Task 5: 接回主流程

### 目标

让第三阶段最小骨架接到现有批量流程里。

### 建议改动文件

- `batch_generator.py`

### 接法建议

不要大改原主流程。

推荐：

1. 保持原有单视频流程不动
2. 新增一个可选入口
3. 多视频模式默认关闭

### 不要做

- 不要把单视频流程打烂
- 不要重构整个 `batch_generator.py`

### 验收标准

- 单视频模式照旧
- 多视频模式有单独开关或单独入口

---

## Task 6: 第三阶段文档

### 目标

补 1 份第三阶段说明文档。

### 建议文件

- `docs/phase3_multi_video.md`

### 文档内容

只写：

- 目标
- 当前最小实现
- 文件位置
- 评分逻辑
- 留白位置

不要写太长。

---

## 总体要求

第三阶段只求：

- 骨架清楚
- 主流程可读
- 后续容易修

不求：

- 一步做到很智能
- 一步做到很完整
