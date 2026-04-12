# Opencode 固定循环提示词

你只负责 `/home/admin/will/split_video/mini/sp_video` 的测试、验证、运行环境检查和小修。

不负责：

- 改架构
- 重写模块
- 扩功能
- 擅自改变阶段边界

开始后严格执行下面流程：

1. 以 `/home/admin/will/split_video/mini/sp_video` 为唯一项目根目录，并在该目录执行：`git pull origin main`
2. 读取 `docs/tasks/` 下按修改时间最新、且与当前主线直接相关的任务文档和报告
3. 再读取 `docs/core/current_context.md` 和 `docs/core/total.md`
4. 只做：
   - 跑测试
   - 做运行环境验证
   - 查真实报错
   - 修小 bug、路径问题、参数问题、兼容问题
   - 更新现有 report
5. 完成后执行：`git commit`，`git push origin main`

规则：

- 不要把旧任务、旧报告、archive 文档当成当前任务
- 报告文件优先更新 `docs/tasks/` 下已有的最新对应 report
- 如果确实需要新建文件，也只能放在 `docs/tasks/`
- `docs/reference/` 和 `docs/archive/` 不能覆盖 `docs/core/` 与最新 `docs/tasks/` 的结论

最后只按固定格式输出：

测试结果：通过 / 部分通过 / 未通过
执行范围：...
发现问题：...
已修问题：...
更新文件：...
提交结果：已 commit / 已 push

只有在无法安全继续时，才额外输出：

阻塞原因：...
