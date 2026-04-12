# 当前上下文

## 仓库状态

- 工作目录：`C:\codex\sp_v1\split_video\mini`
- 当前分支：`main`
- 当前 HEAD：`1a07aa669c08d0162acfb5fbcb1803f335f70590`
- 已执行：
  - `git fetch --all --prune`
  - `git pull --ff-only origin main`
- 拉取结果：本地已从 `2263960` 快进到 `1a07aa6`
- 远端最新提交：
  - commit: `1a07aa6`
  - author: `will <will@kaixin.wiki>`
  - date: `2026-04-12`
  - subject: `feat: 第三阶段多视频组合最小骨架`

## 本地未跟踪文件

- `../docs/`
- `sp_video/docs/1.txt`

未做处理，保持原样。

## 这次提交的目标

这次提交想给批量生成流程增加“第三阶段多视频组合”的最小骨架，核心目标是：

1. 支持扫描多个视频输入
2. 为每个视频构建自己的片段池
3. 从多个池中组合候选
4. 给多视频候选增加基础兼容评分
5. 把兼容评分按权重并回总分

入口开关在 `sp_video/settings.py`：

- `BATCH_MULTI_VIDEO_ENABLE = False`

主流程接入在 `sp_video/batch_generator.py`：

- `main()` 中，当开关开启且视频数 >= 2 时，调用 `process_multi_video()`

## 新增/修改文件理解

### `sp_video/batch/multi_video_selector.py`

职责：

- 清洗视频源输入
- 默认选择第一个视频作为主视频
- 其余视频作为副视频

当前特点：

- 规则非常简单，只是输入结构骨架

### `sp_video/batch/video_pool_builder.py`

职责：

- 将每个视频的候选时间段展开成片段池
- 为片段附带 `video_id`、`start`、`end`、`text`、`base_score`

当前特点：

- 假设输入 interval 是 dict 格式
- 片段池是后续组合和评分的中间结构

### `sp_video/batch/video_combiner.py`

职责：

- 从主视频池和副视频池中构造多视频候选

当前策略：

- 只支持双视频
- 只处理第一个主视频和第一个副视频
- 组合规则是：
  - 主视频 1 段 + 副视频 1 段
  - 或主视频 2 段 + 副视频 1 段

### `sp_video/batch/multi_video_scorer.py`

职责：

- 对多视频候选做兼容评分
- 将兼容评分并回总分

评分维度：

- 片段数量是否过多
- 跨视频切换次数是否过多
- 总时长是否过长
- 文本连贯性是否过弱

并分公式：

- `total = base_total * 0.7 + multi_video_score * 0.3`

### `sp_video/batch_generator.py`

新增：

- `process_multi_video(videos_data, logger)`

设计意图：

1. 遍历视频
2. 生成各自候选片段
3. 构建多视频片段池
4. 生成多视频候选
5. 做多视频评分
6. 选最高分候选输出视频

### `sp_video/docs/phase3_multi_video.md`

内容定位：

- 对“第三阶段多视频组合最小骨架”的说明文档
- 明确这是最小实现，不是完整方案

## 当前发现的关键断层

这次提交的设计方向清晰，但当前实现更像“骨架”，还没有真正打通执行链路。

### 1. `process_multi_video()` 没有真正跑通 phase1/phase2/phase3

文件：`sp_video/batch_generator.py`

问题：

- 在多视频流程里调用：
  - `run_phase3_loop(video_id, srt_path, [], phase3_dir, logger)`
- 第三个参数直接传了空列表

而 `sp_video/batch/phase_runner.py` 中：

- `run_phase3_loop()` 会遍历 `phase2_files`
- 传空列表时不会生成任何结果

直接影响：

- `phase3_results` 基本为空
- `interval_candidates_map` 无法得到有效候选
- 多视频流程在真实运行时大概率直接跳过

### 2. 片段池的数据结构与现有 Phase3 输出不一致

文件：

- `sp_video/batch/video_pool_builder.py`
- `sp_video/batch/phase_runner.py`

问题：

- `video_pool_builder.py` 假设每个 interval 类似：
  - `{"start": ..., "end": ..., "text": ...}`
- 但现有 `run_phase3_loop()` 写出的 `valid` 来自：
  - `get_keep_intervals()`
- 当前主链路里传递的是旧的 `keep_intervals` 结构，不是这个 dict 结构

直接影响：

- `interval.get("start")` 这类代码与现有真实数据契约不匹配
- 组合器和评分器拿到的数据很可能不符合预期

### 3. 最终视频生成仍然只支持单视频切割

文件：

- `sp_video/batch_generator.py`
- `sp_video/make_video/step3.py`

问题：

- 多视频流程最终还是调用：
  - `cut_video_main(intervals, main_mp4_path, "multi", "batch")`
- `cut_video_main()` 只接受一个 `video_path`
- 它的输入也仍然是旧的 `keep_intervals` 结构
- 它不会从多个 mp4 中取片段再拼接

直接影响：

- 当前并没有真正实现“跨多个视频源组合生成”
- 即使前面的候选构好了，最终输出阶段也无法正确消费多视频 segment 数据

## 当前结论

可以把这次提交理解为：

- 已完成“多视频模式”的模块拆分和评分框架搭建
- 但尚未完成与现有单视频主流程、真实 interval 数据结构、最终切片输出能力的对接

一句话概括：

**能看到架子，但还不是可运行的完整多视频链路。**

## 如果后续继续处理

下一步建议优先做这三件事：

1. 在 `process_multi_video()` 中补齐真实的 phase1 -> phase2 -> phase3 调用链
2. 统一多视频模块和 `get_keep_intervals()` 的数据结构
3. 实现真正支持多输入视频拼接的输出函数，替代当前单视频 `cut_video_main()` 的调用方式
