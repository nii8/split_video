# 启动提示词

先以 `C:\codex\sp_v1\split_video\mini\sp_video` 为唯一项目根目录。

你的目标不是全量巡检所有非代码文件，而是用最小必要上下文恢复当前主线，然后继续推进。

这次恢复上下文时，要特别记住：

- 用户最稀缺的资源是注意力，不是 token 本身
- token、文档、提示词都只是为了减少注意力浪费
- 默认目标不是“把话说全”，而是“在不跑偏的前提下少打断用户”
- 能通过核心文档和代码自行判断的，不要再抛回给用户
- 能沉淀成规则的，不要让用户下次重复解释

## 固定读取顺序

恢复上下文时，严格按下面顺序读取：

1. `docs/core/current_context.md`
2. `docs/core/total.md`
3. `docs/core/user_working_style.md`
4. `docs/core/user_query_analysis.md`
5. `docs/core/batch_generator_v2_roadmap.md`
6. `docs/core/project_mainline_2026_04_12.md`
7. `docs/core/coding_style_preference.md`
8. `docs/tasks/` 下按修改时间最新、且与当前主线直接相关的任务文档、实现报告、测试报告、根因报告

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

如果核心文档已经足够，就不要为了“显得全面”去扩读更多文件。

## 任务判定规则

- `docs/tasks/` 必须先按修改时间排序，再判断哪些文件和当前主线直接相关
- 不要把旧任务、旧测试、旧实现报告当成当前任务
- `docs/reference/` 和 `docs/archive/` 不能覆盖 `docs/core/` 与最新 `docs/tasks/` 的结论
- 如果 `user_working_style.md` 与 `user_query_analysis.md` 已经说明了用户协作偏好，就不要在当前会话里重复试探用户

## 注意力保护规则

- 默认先推进能确定的部分，再在关键节点请求用户拍板
- 默认减少用户决策次数，而不是制造更多确认步骤
- 优先输出结论、动作、下一步，不要先铺很长背景
- 不要把“优化流程本身”放在“推进主线结果”之前，除非用户明确要求

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
