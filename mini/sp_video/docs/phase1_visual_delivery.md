# 第一阶段交付说明

## 这次交付了什么

这次交付的是：

- 在现有批量生成流程里，补上第一阶段“视觉评分”的最小代码骨架

目标不是一步到位，而是先把下面这条链路补进去：

1. 拿到 `intervals`
2. 对视频片段抽帧
3. 固定拼成 9 宫格
4. 调多模态模型评分
5. 把 `visual_score` 合并回候选总分

---

## 已新增/整理的文件

### 1. `batch/frame_sampler.py`

作用：

- 把视频片段按固定时间间隔抽成多张图

核心函数：

- `srt_time_to_seconds()`
- `build_sample_timestamps()`
- `sample_frames_for_interval()`
- `sample_frames_for_intervals()`

---

### 2. `batch/image_grid.py`

作用：

- 把抽出来的图片固定拼成 `3x3` 的 9 宫格图

核心函数：

- `pad_images_for_grid()`
- `make_grid_image()`

说明：

- 这里已经固定就是 9 宫格
- 不做动态布局

---

### 3. `batch/visual_scorer.py`

作用：

- 负责第一阶段视觉评分的主逻辑

核心函数：

- `score_candidate_visual()`
- `score_interval_visual()`
- `fake_visual_score()`
- `call_visual_llm()`
- `parse_visual_score_response()`
- `merge_interval_and_visual_score()`
- `enrich_top_interval_candidates_with_visual_score()`

说明：

- `use_llm=False` 时走假评分，用来先打通流程
- `use_llm=True` 时走真实多模态评分

---

### 4. `batch/visual_debug.py`

作用：

- 在项目完整环境里，单独调一个时间段做视觉评分调试

适合场景：

- 已有 `settings.py`
- 已有 API key
- 想快速验证项目环境是否能跑通

---

### 5. `batch/visual_debug_standalone.py`

作用：

- 不依赖 `settings.py` 的独立调试脚本

适合场景：

- 只想单独验证抽帧、拼图、多模态评分
- 不想先依赖整个项目配置

---

### 6. `batch_generator.py`

作用：

- 已经接入第一阶段视觉评分的插入点

接入位置：

- 在 Phase4 基础评分之后
- 在 Phase5 生成视频之前

当前策略：

- 只给前几个候选补一层 `visual_score`
- 不改原来的主流程

---

### 7. `docs/phase1_visual_scoring.md`

作用：

- 第一阶段的说明文档

适合：

- 先读流程
- 再读代码

---

## 当前主流程是怎样接进去的

在 `batch_generator.py` 里，现在流程是：

1. Phase1：字幕筛选
2. Phase2：脚本生成
3. Phase3：时间轴匹配
4. Phase4：原有规则评分
5. 第一阶段新增：视觉评分
6. Phase5：最终生成视频

也就是说：

- 视觉评分不是替代原评分
- 而是在原评分基础上，补一层画面判断

---

## 当前保留的留白

有几处是故意留给后续运行环境继续修的：

### 1. `ffmpeg`

当前抽帧直接写死 `ffmpeg` 命令。

如果运行环境里：

- 路径不同
- 命令名不同
- 参数需要调整

就改 `batch/frame_sampler.py` 里的 `sample_frames_for_interval()`。

---

### 2. 多模态模型名

当前默认：

- `qwen-vl-max`

如果后续运行环境需要换模型，改 `visual_scorer.py` 里的：

- `call_visual_llm()`

---

### 3. 模型返回格式

当前 `parse_visual_score_response()` 已经做了简单容错：

- 先直接按 JSON 解析
- 不行就正则抓 JSON
- 再不行给默认分

如果后续实际模型输出风格有变化，主要修这里。

---

### 4. 分数合并权重

当前：

- `merge_interval_and_visual_score()` 里默认视觉分权重是 `0.2`

如果后续觉得：

- 视觉权重太高
- 或太低

就直接改这里。

---

## 当前建议的调试顺序

后续在真正运行环境里，建议按这个顺序测：

### 第一步

先测：

- `batch/visual_debug_standalone.py`

目的：

- 只验证抽帧
- 拼图
- 模型返回

示例：

```bash
python batch\\visual_debug_standalone.py ^
  --video_path xxx.mp4 ^
  --start 00:00:10,000 ^
  --end 00:00:28,000 ^
  --api_key your_key
```

---

### 第二步

再测：

- `batch/visual_debug.py`

目的：

- 验证项目里的 `settings.py`
- 验证项目环境里的 API key 和路径

示例：

```bash
python batch\\visual_debug.py ^
  --video_id C1873 ^
  --video_path data\\hanbing\\C1873\\C1873.mp4 ^
  --start 00:00:10,000 ^
  --end 00:00:28,000 ^
  --use_llm
```

---

### 第三步

最后再打开：

- `settings.py` 里的视觉评分开关

主要配置是：

- `BATCH_VISUAL_ENABLE`
- `BATCH_VISUAL_TOPN`
- `BATCH_VISUAL_USE_LLM`

目的：

- 验证视觉分是否真正影响候选排序

---

## 当前代码风格说明

这批代码是按当前项目已有风格写的：

- 过程式
- 少抽象
- 不上 class
- 固定 9 宫格
- 主流程优先可读

目标不是“设计得很漂亮”，而是：

- 人能 review
- 后续模型能接手修
- 出问题时容易 debug

---

## 一句话总结

第一阶段现在已经不是“想法”，而是：

- 代码骨架已接进主流程
- 调试入口已准备好
- 留白位置也写清楚了

后续运行环境只需要补真实依赖、真实视频和真实 API 验证即可。
