# Total

## 文档角色

这份文档不再承担“所有上下文的大杂烩”角色。

它现在只做两件事：

1. 作为 `docs/core/` 的入口索引
2. 记录长期有效的协作规则

当前项目状态、阶段判断、主线目标，请优先读：

- `docs/core/current_context.md`

---

## 推荐读取顺序

恢复上下文时，默认按下面顺序读：

1. `docs/core/current_context.md`
2. `docs/core/total.md`
3. `docs/core/batch_generator_v2_roadmap.md`
4. `docs/core/project_mainline_2026_04_12.md`
5. `docs/core/coding_style_preference.md`
6. `docs/tasks/` 下按修改时间最新、且和当前主线直接相关的文档

只有在上面不够时，才读：

- `docs/reference/`
- `docs/archive/`

不要让 `reference` 或 `archive` 覆盖 `core` 和 `tasks` 的最新结论。

---

## Core 文档分工

### `current_context.md`

记录当前主线、当前边界、当前阻塞、当前优先级。

### `total.md`

记录长期协作规则、读文档顺序、固定提示词原则。

### `batch_generator_v2_roadmap.md`

记录 V2 三阶段路线图。

### `project_mainline_2026_04_12.md`

记录项目演进轨迹和主线变化。

### `coding_style_preference.md`

记录代码风格和实现偏好。

---

## 最高优先级规则

### 1. 先 push，再进入测试阶段

只要代码已经写完，并且下一步要交给别人测试：

**必须先 push。**

没有 push，就不算交付。
没有交付，就不允许进入测试协作。

### 2. 当前任务只看最新相关文档

读取任务时，必须：

- 先看 `docs/tasks/` 的修改时间
- 再判断是否和当前主线直接相关
- 只把最新相关文档当作当前任务依据

不要把旧任务、旧报告、旧 handoff 当当前状态。

### 3. 写报告和任务文档时写到固定目录

任务文档、实现报告、测试报告、根因报告，只写到：

- `docs/tasks/`

长期核心结论，只写到：

- `docs/core/`

不要写到临时目录，不要到处散落。

---

## 协作分工

- Codex：代码实现、主线判断、任务编排
- Opencode：真实环境测试、验证、小修
- Claude / claude-cli：架构评估、风险判断
- 用户：给目标、转发固定提示词、贴结果截图、在方向变化时拍板

---

## 自动推进原则

默认情况下：

1. Codex 先读取最新代码和最新核心文档
2. 判断当前主矛盾
3. 直接写代码，或给 Opencode 写下一轮测试任务
4. Opencode `git pull origin main`
5. Opencode 只做测试、验证、小修
6. Opencode 更新 `docs/tasks/` 里的对应 report
7. Opencode `git commit` + `git push origin main`
8. 用户贴结果
9. Codex 再继续下一轮

只有遇到下面情况才停下来问用户：

- 要改变总目标
- 要改变阶段边界
- 要做明显高风险/大改
- 发现当前方案走不通
- 发现代码与核心文档严重冲突，无法安全判断

---

## 固定提示词要求

固定提示词的目标不是短，而是：

- 读取路径固定
- 文档优先级固定
- 最新任务识别规则固定
- 输出格式固定
- 职责边界固定

以后固定提示词必须明确：

1. 唯一项目根目录
2. 先读 `docs/core/`，再读 `docs/tasks/`
3. `docs/tasks/` 必须按修改时间找最新相关文件
4. `docs/reference/` 和 `docs/archive/` 不能覆盖最新核心结论
5. Opencode 只做测试、验证、小修，不改架构
6. 最终输出必须使用固定摘要格式

---

## 一句话原则

`docs/core/` 要尽量少而准。

项目状态统一收口到 `current_context.md`；
长期规则统一收口到 `total.md`；
一次性交接和重复上下文不再保留在核心路径里。
