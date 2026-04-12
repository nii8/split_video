# Codex 固定循环提示词

继续自动推进 `C:\codex\sp_v1\split_video\mini\sp_video` 主线。

先按固定顺序读取：

1. `docs/core/current_context.md`
2. `docs/core/total.md`
3. `docs/tasks/` 下按修改时间最新、且与当前主线直接相关的文档

必要时再补读：

- `docs/core/batch_generator_v2_roadmap.md`
- `docs/core/project_mainline_2026_04_12.md`
- `README.md`
- `ARCHITECTURE.md`
- `CLAUDE.md`
- `docs/reference/` 下必要文件

不要默认全量扫描全部非代码文件。
不要把旧任务、旧报告、archive 文档当成当前任务。

结合最新代码和最新文档，判断当前主矛盾，然后直接执行最该做的事：

- 如果该继续实现，就直接写代码推进主线
- 如果该继续测试，就写给 Opencode 的下一轮任务
- 如果该先分析结果，就先基于最新代码和最新报告判断

默认不要停下来问我。只有在下面情况才停：

- 需要改变总目标
- 需要改变阶段边界
- 需要做明显高风险或大改
- 发现当前方案走不通
- 发现核心文档与代码严重冲突，无法安全判断

输出时只用固定格式：

本轮判断：...
本轮动作：写代码 / 写任务 / 分析结果
本轮产出：...
下一步给 Opencode：...

只有在必须由我拍板时，才额外输出：

需要确认：...
