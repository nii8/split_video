# Total — 入口索引与核心价值观

更新时间：2026-04-13（Asia/Shanghai）

## 文档角色

这份文档做两件事：

1. 作为 `docs/core/` 的入口索引
2. 记录长期有效的核心价值观

项目当前状态、阶段判断、主线目标，优先读：

- `docs/core/current_context.md`

---

## 核心价值观

这套协作系统长期优先保护的不是"表面工作量"，而是：

1. 用户注意力
2. 清晰主线
3. 可靠交付
4. 可复用机制

其中最稀缺的资源是：

**用户的高价值注意力。**

所以以后任何协作设计、提示词设计、文档设计，都要优先满足下面几条：

- 少让用户重复解释相同上下文
- 少让用户在低价值细节上反复拍板
- 少让系统因为读错文档、读错目录、读错旧任务而消耗用户
- 把一次性判断尽量沉淀为长期规则
- 能自动推进的，不要反复打断用户

一句话：

**系统的职责是替用户吸收复杂度，而不是把复杂度转嫁给用户。**

---

## 推荐读取顺序

恢复上下文时，默认按下面顺序读：

1. `docs/core/current_context.md`
2. `docs/core/goals.md`
3. `docs/core/collaboration.md`
4. `docs/core/batch_generator_v2_roadmap.md`
5. `docs/core/rules.md`（只有涉及规则判断时才读）
6. `docs/tasks/` 下按修改时间最新、且和当前主线直接相关的文档

只有在上面不够时，才读：

- `docs/core/user_working_style.md`（了解用户协作偏好时读）
- `docs/core/attention_and_recovery.md`（发现沟通出现问题时读）
- `docs/core/coding_style_preference.md`（涉及代码风格判断时读）
- `docs/reference/`
- `docs/archive/`

不要让 `reference` 或 `archive` 覆盖 `core` 和 `tasks` 的最新结论。

---

## Core 文档分工

### `current_context.md`

记录当前主线、当前边界、当前阻塞、当前优先级。**频繁更新。**

### `goals.md`

记录当前统一的终极目标、近期目标和当前重点。**目标唯一权威来源。**

### `rules.md`

记录所有长期固定规则。**规则唯一权威来源。**

### `collaboration.md`

记录角色分工、自动推进流程、固定提示词设计原则。**协作机制唯一权威来源。**

### `attention_and_recovery.md`

记录注意力保护原则 + 崩溃检测与修复流程。**注意力保护唯一权威来源。**

### `user_working_style.md`

记录用户长期稳定的工作风格、优势、风险和协作注意事项。

### `coding_style_preference.md`

记录代码风格和实现偏好。

### `batch_generator_v2_roadmap.md`

记录 V2 三阶段技术路线图。

---

## 归档文件（docs/archive/）

- `project_mainline_2026_04_12.md`：项目演进轨迹历史记录（只读）
- `user_query_analysis.md`：用户原始提问分析数据（只读）

默认不作为当前推进依据。

---

## 一句话原则

`docs/core/` 要尽量少而准。

每件事只有一个权威文件，不在多处重复发明。
