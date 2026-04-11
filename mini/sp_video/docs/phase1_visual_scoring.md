# 第一阶段：视觉评分说明

## 目标

这一步不是生成视频，也不是做复杂导演系统。

这一步只做一件事：

- 在原有文本评分之后，补一层画面评分

也就是说，有些候选文本不错，但画面不行，就应该提前扣分，不要等最终生成视频才发现。

---

## 最小流程

第一阶段现在的代码按下面顺序工作：

1. 先拿到 `intervals`
2. 对每个时间段抽图
3. 固定拼成 9 宫格
4. 用多模态模型打分
5. 得到 `visual_score`
6. 把 `visual_score` 合并回原来的候选总分

---

## 相关文件

- `batch/frame_sampler.py`
  - 负责抽帧

- `batch/image_grid.py`
  - 负责拼 9 宫格

- `batch/visual_scorer.py`
  - 负责假评分、真评分、结果合并

- `batch/visual_debug.py`
  - 依赖项目环境的调试入口

- `batch/visual_debug_standalone.py`
  - 不依赖 `settings.py` 的独立调试入口

---

## 设计原则

- 9 宫格固定，不做动态布局
- 函数尽量短，过程式为主
- 不上 class
- 能写死的先写死
- 留出后续修复位置，但不先过度设计

---

## 当前留白

第一阶段有几处是故意留给后续运行环境修的：

1. `frame_sampler.py` 里直接写了 `ffmpeg`
   - 如果运行环境命令不同，改这里

2. `visual_scorer.py` 里模型名默认是 `qwen-vl-max`
   - 如果后续环境要换模型，改这里

3. `parse_visual_score_response()`
   - 现在已经做了简单容错
   - 如果模型输出风格变了，主要修这里

4. `merge_interval_and_visual_score()`
   - 现在视觉分默认权重是 `0.2`
   - 如果后续觉得视觉影响太大或太小，改这里

---

## 建议的后续测试顺序

后续在真正运行环境中，建议按这个顺序测：

1. 先测 `visual_debug_standalone.py`
   - 只验证抽帧、拼图、模型返回是否正常

2. 再测 `visual_debug.py`
   - 验证项目环境里的 `settings.py`、API key、路径是否正常

3. 最后再打开 `batch_generator.py` 里的视觉评分开关
   - 验证视觉分能否影响最终候选排序

---

## 一句话总结

第一阶段不是要把事情做复杂，而是先把“这段画面值不值得上屏”这件事补进现有流程里。
