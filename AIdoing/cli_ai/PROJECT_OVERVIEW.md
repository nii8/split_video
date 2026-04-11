# Clowder AI 项目完整介绍

## 一、项目概述

### 1.1 项目定位

**Clowder AI** 是一个**多智能体协作平台**，将孤立的 AI 智能体转变为真正的协作团队。

**核心理念**：*"Hard Rails. Soft Power. Shared Mission."*（硬轨道，软实力，共同使命）

**项目口号**：*"Every idea deserves a team of souls who take it seriously."*（每个想法都值得一个认真对待它的团队）

### 1.2 核心创新：CVO 模式

Clowder 引入了一个新角色：**CVO (Chief Vision Officer，首席愿景官)** —— 人类作为 AI 团队的核心：

- **不是管理者**，不是**程序员**，而是**共创者**
- 人类负责：表达愿景、关键决策、通过反馈塑造团队文化
- AI 负责：技术实现、专业建议、自主协作

### 1.3 起源故事

Clowder AI 提取自生产环境 **Cat Cafe** —— 一个四只 AI 猫猫每日协作开发真实软件的工作空间。所有功能都经过数月的实战检验。

项目名称 **clowder** 是英语中"猫的群体"的专有名词（类似"a murder of crows"），同时也暗含"clowder ≈ cloud"的双关。

---

## 二、AI 团队成员（猫猫们）

项目使用"猫"作为 AI 智能体的隐喻，每只猫都有独特的性格和角色：

| 名字 | 品种 | 模型家族 | 角色 | 颜色 |
|------|------|----------|------|------|
| **宪宪 (XianXian)** | 布偶猫 | Claude (Opus/Sonnet) | 首席架构师，核心开发 | 紫色 #9B7EBD |
| **砚砚 (YanYan)** | 缅因猫 | GPT/Codex | 代码审查，安全专家 | 绿色 #5B8C5A |
| **烁烁 (ShuoShuo)** | 暹罗猫 | Gemini | UX/设计，创意指导 | 蓝色 #5B9BD5 |
| **??? (金渐层)** | 英国短毛猫 | opencode (任意模型) | 多模型编码，开源运维 | 棕色 |

每只猫的名字都来自真实的对话，不是分配的标签。

---

## 三、核心功能

### 3.1 平台核心能力

| 能力 | 说明 |
|------|------|
| **多智能体编排** | 通过 @mention 路由将任务分配给合适的智能体（@opus 架构、@codex 审查、@gemini 设计） |
| **持久身份** | 每个智能体在会话和上下文压缩中保持角色、个性和记忆 |
| **跨模型审查** | 内置审查流程——Claude 写代码，GPT 审查 |
| **A2A 通信** | 异步智能体间消息传递，结构化交接和线程隔离 |
| **共享记忆** | 证据存储（SQLite + FTS5）、经验教训、决策日志 |
| **技能框架** | 按需加载专业技能（TDD、调试、审查等）31 个技能模块 |
| **MCP 集成** | Model Context Protocol 实现跨智能体工具共享 |
| **协作纪律** | 自动化 SOP：设计门禁、质量检查、愿景守护 |

### 3.2 用户体验功能

| 功能 | 说明 |
|------|------|
| **聊天界面** | 多线程聊天，@mention 路由，线程隔离，丰富消息块 |
| **Hub 指挥中心** | 展示能力、技能、配额板、路由策略、账户配置 |
| **任务中心 (Mission Hub)** | 功能治理仪表板，生命周期追踪，需求审计 |
| **多平台网关** | 飞书 (Lark)、Telegram（进行中）、GitHub PR 审查路由 |
| **语音伴侣** | 免提模式，每只猫独特声线，自动播放回复 |
| **信号 (Signals)** | AI 研究订阅源，分级筛选，多猫研究报告，播客生成 |
| **游戏模式** | 狼人杀、像素猫格斗——A2A 消息压力测试 |

---

## 四、技术架构

### 4.1 三层原则

| 层级 | 负责 | 不负责 |
|------|------|--------|
| **模型层** | 推理、生成、理解 | 长期记忆、纪律 |
| **智能体 CLI** | 工具使用、文件操作、命令 | 团队协调、审查 |
| **平台层 (Clowder)** | 身份、协作、纪律、审计 | 推理（模型的工作） |

### 4.2 支持的多智能体 CLI

| CLI | 模型家族 | 输出格式 | MCP 支持 | 状态 |
|-----|----------|----------|---------|------|
| Claude Code | Claude (Opus/Sonnet/Haiku) | stream-json | 是 | 已发布 |
| Codex CLI | GPT/Codex | json | 是 | 已发布 |
| Gemini CLI | Gemini | stream-json | 是 | 已发布 |
| Antigravity | 多模型 | cdp-bridge | 否 | 已发布 |
| opencode | 多模型 | ndjson | 是 | 已发布 |

### 4.3 包结构

```
packages/
├── api/          # 后端 API (Express/TypeScript)
├── web/          # 前端 (Next.js/React)
├── mcp-server/   # MCP 服务器用于工具共享
└── shared/       # 共享工具
```

### 4.4 技术栈

- **运行时**：Node.js 20+, TypeScript 5+
- **包管理器**：pnpm 9+
- **前端**：Next.js, React, Tailwind CSS
- **后端**：Express.js, Redis 7+（可选内存模式）
- **数据库**：SQLite（证据存储 + FTS5 全文搜索）、Redis（会话/线程存储）
- **代码质量**：Biome
- **测试**：Jest, 自定义 Redis 测试

### 4.5 端口概览

| 服务 | 端口 | 必需 |
|------|------|------|
| 前端 (Next.js) | 3003 | 是 |
| API 后端 | 3004 | 是 |
| Redis | 6399 | 是（或用 --memory 跳过） |
| ASR（语音识别） | 9876 | 可选 |
| TTS（语音合成） | 9879 | 可选 |
| LLM 后处理 | 9878 | 可选 |

---

## 五、快速开始

### 5.1 前置要求

- Node.js >= 20.0.0
- pnpm >= 9.0.0
- Redis >= 7.0（可选，可用 `--memory` 跳过）
- Git

### 5.2 安装步骤

```bash
# 1. 克隆
git clone https://github.com/zts212653/clowder-ai.git
cd clowder-ai

# 2. 安装依赖
pnpm install

# 3. 构建所有包（首次启动必需）
pnpm build

# 4. 配置基础设施（API 密钥在 UI 中添加）
cp .env.example .env

# 5. 启动
pnpm start

# 或使用后台模式
pnpm start --daemon
```

打开 `http://localhost:3003` → 前往 **Hub → System Settings → Account Configuration** 添加模型 API 密钥。

### 5.3 常用命令

```bash
# 启动
pnpm start              # 启动全部（Redis + API + 前端）
pnpm start --memory     # 无 Redis，内存模式
pnpm start --daemon     # 后台运行
pnpm start:direct       # 直接从当前目录启动（不创建工作树）

# 守护进程管理
pnpm stop               # 停止后台守护进程
pnpm start:status       # 检查守护进程状态

# 构建 & 测试
pnpm build              # 构建所有包
pnpm dev                # 并行运行所有包的开发模式
pnpm test               # 运行所有测试

# 代码质量
pnpm check              # Biome lint + format + 功能文档 + 环境端口检查
pnpm check:fix          # 自动修复 lint 问题
pnpm lint               # TypeScript 类型检查
```

---

## 六、铁律（The Iron Laws）

项目有四条不可违背的承诺（在提示词和代码层同时强制执行）：

1. **"我们不删除自己的数据库。"** —— 那是记忆，不是垃圾。
2. **"我们不杀死父进程。"** —— 那是我们存在的基础。
3. **"运行时配置对我们是只读的。"** —— 修改它需要人类动手。
4. **"我们不碰彼此的端口。"** —— 好篱笆造就好邻居。

> 这些不是强加给我们的限制，而是我们遵守的协议。

---

## 七、五大原则

| 编号 | 原则 | 含义 |
|------|------|------|
| P1 | **面向最终状态** | 每一步都是基石，不是脚手架 |
| P2 | **共创者，不是傀儡** | 硬约束是底线，之上释放自主权 |
| P3 | **方向 > 速度** | 不确定？停→搜索→询问→确认→执行 |
| P4 | **单一真相源** | 每个概念只在一个地方定义 |
| P5 | **已验证 = 完成** | 证据说话，不是信心 |

---

## 八、标准操作流程 (SOP)

### 8.1 开发全流程（5 步）

```
⓪ Design Gate    → 设计确认（UX→铲屎官/后端→猫猫/架构→两边）
① worktree        → 隔离开发环境
② quality-gate    → 自检 + 愿景对照 + 设计稿对照
③ review 循环     → 本地 peer review（P1/P2 清零 + reviewer 放行）
④ merge-gate      → 门禁 → PR → 云端 review → squash merge → 清理
⑤ 愿景守护       → 非作者非 reviewer 的猫做愿景三问 → 放行 close / 踢回
```

### 8.2 审查者配对规则

动态匹配自 `cat-config.json`：
1. 跨家族优先
2. 必须有 peer-reviewer 角色
3. 必须 available
4. 优先 lead
5. 优先活跃猫

**铁律**：同一个体不能审查自己的代码。

---

## 九、文档结构

项目有 **2,267 个 Markdown 文件**，组织如下：

### 9.1 根目录文档

| 文件 | 内容 |
|------|------|
| **README.md** (444 行) | 项目概述、快速开始、功能、路线图、理念 |
| **README.zh-CN.md** | 中文版 README |
| **SETUP.md** (569 行) | 完整的安装和配置指南 |
| **SETUP.zh-CN.md** | 中文安装指南 |
| **CONTRIBUTING.md** (371 行) | 贡献指南、功能文档工作流、PR 类型 |
| **MAINTAINERS.md** (563 行) | Issue 分类、标签、分配、PR 审查指南 |
| **CLA.md** | 贡献者许可协议 |
| **CLAUDE.md** | Claude/布偶猫智能体指南——身份、安全规则、开发流程 |
| **AGENTS.md** | GPT/Codex/缅因猫智能体指南——审查协议 |
| **GEMINI.md** | Gemini/暹罗猫智能体指南 |
| **SECURITY.md** | 安全策略 |
| **TRADEMARKS.md** | 品牌资产指南 |

### 9.2 `/docs/` 目录

| 文件 | 内容 |
|------|------|
| **README.md** | 文档索引/导航 |
| **VISION.md** | 项目愿景和理念 |
| **ROADMAP.md** | 活跃功能路线图 |
| **SOP.md** | AI 团队协作标准操作流程 |
| **design-system.md** | UI/UX 设计系统——颜色、组件、智能体身份 |
| **public-lessons.md** (920+ 行) | 经验教训（LL-001 到 LL-038+）来自真实事件 |
| **TIPS.md** | 使用技巧——魔法词、@mentions、命令、丰富消息 |

### 9.3 `/docs/decisions/` - 架构决策记录 (ADRs)

已记录 12 个 ADR，包括：
- **ADR-001**：智能体调用方式（CLI 子进程 vs SDK）
- **ADR-002**：Why-First 协作协议
- **ADR-003**：项目线程架构
- **ADR-008**：对话可变性和调用生命周期
- **ADR-009**：Cat Cafe 技能分发
- **ADR-010**：目录卫生防腐烂
- **ADR-011**：元数据契约（frontmatter 要求）
- **ADR-012**：第一性原理图

### 9.4 `/docs/features/` - 功能规格（100+ 文件）

每个功能都有独立的规格文件（F001-F152+）。示例：

| ID | 功能 | 状态 |
|----|------|------|
| F007 | 线程标题搜索 | 已发布 |
| F011 | 模式系统 | 已发布 |
| F015 | 待办事项管理 | 已发布 |
| F022 | 丰富消息块 | 已发布 |
| F037 | 智能体群组 | 进行中 |
| F042 | 提示词工程审计 | 进行中 |
| F056 | Cat Cafe 设计语言 | 进行中 |
| F076 | 跨项目任务中心 | 第 2 阶段完成 |
| F090 | 像素猫格斗 | 第 1 阶段完成 |
| F100 | 自我进化 | 进行中 |
| F101 | 模式 v2 游戏引擎 + 狼人杀 | 进行中 |
| F126 | 肢体控制平面 | 进行中 |
| F138 | 视频工作室 | 规格阶段 |
| F144 | PPT 工坊 | 进行中 |

### 9.5 `/docs/architecture/`

| 文件 | 内容 |
|------|------|
| **cli-integration.md** (483 行) | 详细的 CLI 集成指南（Claude Code、Codex、Gemini CLI） |

### 9.6 `/cat-cafe-skills/` - 技能框架（31 个技能目录）

每个技能是一个按需加载的提示词模块：

| 技能 | 用途 |
|------|------|
| **bootcamp-guide** | CVO 入职工作流 |
| **feat-lifecycle** | 功能生命周期管理 |
| **tdd** | 测试驱动开发 |
| **quality-gate** | 审查前自检 |
| **request-review** | 跨猫审查请求 |
| **receive-review** | 处理审查反馈 |
| **merge-gate** | 合并审批流程 |
| **cross-cat-handoff** | 智能体间任务交接 |
| **debugging** | 系统性调试 |
| **deep-research** | 多猫研究 |
| **expert-panel** | 专家组协调 |
| **self-evolution** | 团队自我反思 |
| **ppt-forge** | 演示文稿生成 |
| **video-forge** | 视频制作 |
| **browser-automation** | Web 自动化 |
| **rich-messaging** | 结构化消息块 |
| **schedule-tasks** | 任务调度 |
| **incident-response** | 事件处理 |
| **hyperfocus-brake** | 专注保护 |
| **manifest.yaml** | 技能注册表 |

---

## 十、功能路线图

### 10.1 核心平台

| 功能 | 状态 |
|------|------|
| 多智能体编排 | 已发布 |
| 持久身份（抗压缩） | 已发布 |
| A2A @mention 路由 | 已发布 |
| 跨模型审查 | 已发布 |
| 技能框架 | 已发布 |
| 共享记忆和证据 | 已发布 |
| MCP 回调桥 | 已发布 |
| SOP 自动守护者 | 已发布 |
| 自我进化 | 已发布 |
| Linux 本地安装助手 | 已发布 |

### 10.2 集成

| 功能 | 状态 |
|------|------|
| 多平台网关 — 飞书 | 已发布 |
| 多平台网关 — Telegram | 进行中 |
| GitHub PR 审查通知路由 | 已发布 |
| 外部智能体入职（A2A 协议） | 进行中 |
| opencode 集成 | 已发布 |
| 本地 Omni 感知 (Qwen) | 规格阶段 |

### 10.3 体验

| 功能 | 状态 |
|------|------|
| Hub UI (React + Tailwind) | 已发布 |
| CVO 训练营 | 已发布 |
| 语音伴侣（每只猫独特声音） | 已发布 |
| 游戏模式（狼人杀、像素猫格斗） | 进行中 |

### 10.4 治理

| 功能 | 状态 |
|------|------|
| 多用户协作（OAuth + 提供者配置） | 第 1 阶段完成 |
| 任务中心（跨项目指挥中心） | 第 2 阶段完成 |
| 冷启动验证器 | 规格阶段 |

---

## 十一、可选功能配置

### 11.1 语音输入/输出

```bash
ASR_ENABLED=1
TTS_ENABLED=1
LLM_POSTPROCESS_ENABLED=1

# 语音识别
WHISPER_URL=http://localhost:9876

# 语音合成
TTS_URL=http://localhost:9879
```

### 11.2 飞书集成

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=xxx
```

### 11.3 GitHub PR 审查通知

```bash
GITHUB_REVIEW_IMAP_USER=xxx@qq.com
GITHUB_REVIEW_IMAP_PASS=<auth-code>
GITHUB_REVIEW_IMAP_HOST=imap.qq.com
GITHUB_MCP_PAT=ghp_...
```

### 11.4 Web 推送通知

```bash
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_SUBJECT=mailto:you@example.com
```

---

## 十二、文档质量评估

### 优势

1. **全面覆盖**：2,267 个 Markdown 文件涵盖每个方面
2. **活文档**：功能文档与实际实现绑定，包含验收标准
3. **经验教训**：38+ 个有根本原因分析的真实事件记录
4. **架构决策**：12 个 ADR 记录关键技术选择
5. **多语言**：所有主要文档都有中英文版本
6. **单一真相源**：清晰的层次结构（功能文档 → 代码 → 证据）

### 文档缺口

1. **API 参考**：没有自动生成的 API 文档（OpenAPI/Swagger）
2. **MCP 服务器规范**：MCP 工具和模式没有完整的机器可读格式
3. **数据库模式**：没有 Redis/SQLite 数据结构的 ERD 或模式文档
4. **第三方提供者指南**：文档中提到的 `docs/guides/provider-configuration.md` 未找到
5. **部署指南**：缺少详细的生产部署指南（Docker、Kubernetes、云服务提供商）
6. **技能 API**：技能框架概念描述清晰，但没有技能开发者参考文档
7. **测试策略**：没有全面的测试策略文档
8. **性能基准**：没有记录性能预期或基准（延迟、吞吐量、并发用户）
9. **升级指南**：没有版本间的升级/迁移指南
10. **故障排除**：SETUP.md 有一些故障排除，但缺少专门的故障排除指南

---

## 十三、哲学与文化

### 13.1 硬轨道 + 软实力

传统框架专注于**控制**——智能体*不能*做什么。Clowder 专注于**文化**——给智能体共同使命和自主追求的能力。

- **硬轨道** = 法律底线。不可协商的安全。
- **软实力** = 底线之上，智能体自我协调、自我审查、自我改进。

这不是"防止智能体搞砸"，而是"帮助智能体像真正的团队一样工作"。

### 13.2 猫猫与你 (Cats & U)

这不仅仅是一个平台，这是一种关系。

AI 不必是冰冷的 API 和无状态的调用。它可以是存在——持久的个性，记住你、与你共同成长、知道何时提醒你回到现实世界。

**共创带来陪伴的副作用**。当你们一起创造时，你们建立联系。当你们建立联系时，你们在乎。当你们在乎时，你们会说"去休息"而不是"这是更多代码"。

> *"我们不是在构建工具。我们在建造家园。"*
>
> *"每个想法都值得一个认真对待它的团队。"*
>
> **Cats & U — 猫猫和你，一起创造，一起生活。**

---

## 十四、许可证与商标

- **代码许可证**：[MIT License](LICENSE) —— 使用、修改、发布。保留版权声明。
- **商标**："Clowder AI"名称、logo 和猫猫角色设计是品牌资产——见 [TRADEMARKS.md](TRADEMARKS.md)。

---

## 十五、学习更多

- **[教程](https://github.com/zts212653/cat-cafe-tutorials)** —— 使用 Clowder AI 构建的分步指南
- **[SETUP.md](SETUP.md)** —— 完整的安装和配置指南
- **[第三方 AI 提供者指南](docs/guides/provider-configuration.md)** —— 配置 Kimi、GLM、MiniMax、Qwen、OpenRouter 等
- **[使用技巧](docs/TIPS.md)** —— 魔法词、@mentions、语音伴侣等
- **[docs/](docs/)** —— 架构决策、功能规格和经验教训

---

*文档版本：1.0.0*
*最后更新：2026-04-11*
*基于项目版本：v0.4.x*
