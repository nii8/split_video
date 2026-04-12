# 启动提示词

先以 `C:\codex\sp_v1\split_video\mini\sp_video` 为唯一项目根目录。

你的目标不是全量巡检所有非代码文件，而是用最小必要上下文恢复当前主线，然后继续推进。

## 固定读取顺序

恢复上下文时，严格按下面顺序读取：

1. `docs/core/current_context.md`
2. `docs/core/total.md`
3. `docs/core/batch_generator_v2_roadmap.md`
4. `docs/core/project_mainline_2026_04_12.md`
5. `docs/core/coding_style_preference.md`
6. `docs/tasks/` 下按修改时间最新、且与当前主线直接相关的任务文档、实现报告、测试报告、根因报告

## 补充读取规则

只有在上面的文档不足以支持当前任务时，才补读：

- `README.md`
- `ARCHITECTURE.md`
- `CLAUDE.md`
- `docs/reference/` 下必要文件

不要默认阅读：

- 当前目录全部 md / txt
- `docs/reference/` 全部文件
- `docs/archive/` 全部文件
- 旧的 handoff / restart / 临时上下文类文档

## 任务判定规则

- `docs/tasks/` 必须先按修改时间排序，再判断哪些文件和当前主线直接相关
- 不要把旧任务、旧测试、旧实现报告当成当前任务
- `docs/reference/` 和 `docs/archive/` 不能覆盖 `docs/core/` 与最新 `docs/tasks/` 的结论

## 输出规则

完成读取后，先不要长篇复述，只用下面三行输出：

1. 当前主线：...
2. 当前阻塞：...
3. 下一步：...

然后直接继续推进当前目标。

## 只有这些情况才停下来问我

- 需要改变总目标
- 需要改变阶段边界
- 需要做明显高风险或大改
- 发现当前方案走不通
- 发现核心文档与代码严重冲突，无法安全判断
