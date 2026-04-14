# 多视频最小候选闭环测试任务 v0

请先阅读：

- `docs/tasks/multi_video_task_v0.md`
- `docs/tasks/multi_video_impl_report.md`

然后：

1. 按任务描述运行代码
2. 检查：
   - 是否能跑
   - 是否有空数据
   - 数据结构是否正确

允许：

- 修小 bug
- 修路径/参数问题

不允许：

- 改架构
- 重写模块

最后输出：

- `docs/tasks/multi_video_test_report.md`

内容：

- 是否跑通
- 有哪些问题
- 修了哪些问题

然后提交 git

---

## 补充说明

### 本次测试目标

本次目标是：

- 验证“多视频最小候选闭环”是否成立
- 当前只验证候选和 `summary.json`
- 不要求生成实际多视频 `.mp4`

### 测试前提

需要满足：

1. 已拉取最新代码
2. `settings.py` 中：

```python
BATCH_MULTI_VIDEO_ENABLE = True
```

3. `data/hanbing/` 下至少有 2 个视频目录
4. 每个目录中至少包含：
   - `{video_id}.mp4`
   - `{video_id}.srt`

### 建议执行命令

```bash
cd mini/sp_video
python batch_generator.py
```

### 重点检查项

1. 是否进入多视频模式
2. 每个视频是否真实跑完 `phase1 -> phase2 -> phase3`
3. 是否生成了有效 `segments`
4. 是否生成非空候选
5. 是否写出：

```text
data/batch_results/multi_video/summary.json
```

6. `summary.json` 是否至少包含：
   - `total_candidates`
   - `top_candidates`
   - `source_videos`

### 不要误报为 bug 的内容

下面这些当前不算 bug：

- 没有生成 `.mp4`
- 没有调用 `cut_video_main()`
- 只输出候选和 `summary.json`

### 允许修的小问题范围

- 小拼写问题
- 小字段问题
- 小路径问题
- 小参数问题
- 小 JSON 结构问题
- 明显低风险的小 bug

超出这个范围，就直接写进 `multi_video_test_report.md`，不要扩写。

---

## 可直接发给 opencode 的一句话

你只做测试和小修。先阅读 `docs/tasks/multi_video_task_v0.md` 和 `docs/tasks/multi_video_impl_report.md`，然后在真实运行环境里执行 `python batch_generator.py`，检查多视频最小候选闭环是否跑通：是否能跑、是否有空数据、数据结构是否正确。你只允许修小 bug 和路径/参数问题，不允许改架构、不允许重写模块。最后输出 `docs/tasks/multi_video_test_report.md`，说明是否跑通、有哪些问题、修了哪些问题，然后提交 git。
