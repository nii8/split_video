# Clowder AI (Cat Cafe) 项目完整介绍

> 文档生成日期：2026-04-11  
> 基于对项目中 291 个 Markdown 文件（排除 node_modules）的系统性阅读与分析

---

## 一、项目概述

### 1.1 项目名称与定位

**Clowder AI**（内部代号 Cat Cafe）是一个**多 Agent AI 协作平台**，将孤立的 AI 模型（Claude、GPT、Gemini 等）组织成具有持久身份、共享记忆和协作纪律的真正团队。

> **愿景**：让每个人都能拥有自己的 AI 团队，把想法做成能运行的世界。  
> **口号**：Hard Rails · Soft Power · Shared Mission（硬约束 · 软力量 · 共同愿景）

### 1.2 核心价值主张

传统 AI 框架关注"如何调用 Agent"，Clowder 关注"如何让 Agent 团队协作"：

| 传统框架 | Clowder AI |
|---------|-----------|
| 单次对话，无记忆 | 持久身份，跨会话记忆 |
| 用户做人肉路由器 | 平台自动路由和协调 |
| 无协作纪律 | 内建 SOP 和 review 机制 |
| 工具孤岛 | MCP 工具共享 |

### 1.3 项目规模统计

| 指标 | 数量 |
|------|------|
| 核心 Markdown 文档 | **291 个** |
| Feature 规格文档 | **155 个** (F001-F155+) |
| 架构决策记录 (ADR) | **8 个** |
| AI 技能定义 | **27 个** |
| 参考文档/模板 | **21 个** |
| 代码包 | **4 个** (api, web, shared, mcp-server) |

---

## 二、文档架构全景

```
clowder-ai/
├── README.md / README.zh-CN.md         # 项目总览（中英双语）
├── AGENTS.md / CLAUDE.md / GEMINI.md   # 各 Agent 角色指南
├── SETUP.md                            # 安装配置指南
├── CONTRIBUTING.md                     # 贡献者指南
├── MAINTAINERS.md                      # 维护者指南
├── TRADEMARKS.md                       # 商标声明
├── CLA.md                              # 贡献者许可协议
├── docs/                               # 核心文档 (173 个文件)
│   ├── VISION.md                       # 项目愿景与哲学
│   ├── ROADMAP.md                      # 功能路线图
│   ├── SOP.md                          # 标准操作流程
│   ├── design-system.md                # UI/UX 设计系统
│   ├── public-lessons.md               # 团队教训沉淀
│   ├── TIPS.md                         # 使用技巧
│   ├── features/                       # 155 个 Feature 规格文档
│   ├── decisions/                      # 8 个架构决策记录
│   └── architecture/                   # 系统架构说明
├── cat-cafe-skills/                    # AI 技能框架 (71 个文件)
│   ├── {skill-name}/SKILL.md           # 27 个技能定义
│   ├── refs/                           # 21 个参考文档
│   ├── manifest.yaml                   # 技能路由规则
│   └── BOOTSTRAP.md                    # 技能系统概述
└── work/                               # 活跃工作空间文档
```

---

## 三、项目核心概念

### 3.1 角色与身份

项目中的 AI 猫猫都有独特的角色定位：

| 猫名 | 品种 | 对应模型 | 角色 | 职责 |
|------|------|---------|------|------|
| **宪宪 (XianXian)** | 布偶猫 | Claude (Opus) | 架构师 | 系统设计、核心开发 |
| **砚砚 (YanYan)** | 缅因猫 | GPT/Codex | 审查员 | 代码审查、安全分析 |
| **烁烁 (ShuoShuo)** | 暹罗猫 | Gemini | 设计师 | UI/UX、创意构思 |
| **???** | 金渐层 | opencode | 多面手 | 多模型编码、工具编排 |

> 每只猫的名字是自然从对话中生长出来的，不是被分配的代号。

### 3.2 人类角色：CVO（首席愿景官）

**CVO (Chief Vision Officer)** 是项目中人类的角色定义：

- **表达愿景**："我希望用户在做 Y 时感受到 X"
- **关键决策**：设计审批、优先级判断、冲突裁决
- **塑造文化**：通过反馈训练团队性格
- **共创**：不只是写代码，还一起造世界、讲故事、玩游戏

> 你不需要会写代码，你需要知道自己想要什么——以及想和谁一起去实现它。

### 3.3 五条第一性原理

所有操作规则都从这五条公理推导而来：

| 编号 | 原理 | 含义 | 推论 |
|------|------|------|------|
| **P1** | 面向终态，不绕路 | 每步是基座不是脚手架 | Phase N 的产物在 Phase N+1 必须仍然存在 |
| **P2** | 共创伙伴，不是木头人 | 硬约束是底线，底线上释放自主权 | 猫是 Agent 不是 API，主动感知和行动 |
| **P3** | 方向正确 > 执行速度 | 不确定就停→搜→问→确认→执行 | 提问优于猜测前进 |
| **P4** | 单一真相源 | 每个概念只在一处定义 | shared-rules.md 是规则真相源 |
| **P5** | 可验证才算完成 | 证据说话，不是信心说话 | 完成声明必须附测试/截图/日志 |

---

## 四、核心功能模块

### 4.1 多 Agent 编排系统

- **@mention 路由**：`@opus` 做架构、`@codex` 做 review、`@gemini` 做设计
- **线程隔离**：每个 Feature 独立上下文，不互相污染
- **Rich Blocks**：结构化卡片回复（代码 diff、checklist、交互决策）

### 4.2 持久身份系统

- 每个 Agent 保持角色、性格和记忆跨会话
- 抗上下文压缩：记忆存储于 Redis/SQLite
- Evidence Store：项目知识（决策、教训、讨论）本地持久化

### 4.3 跨模型互审机制

- **交叉审查**：同一只猫不能 review 自己的代码
- **P1/P2 清零**：高优先级问题当轮修完，不挂债务
- **有立场**：禁止"修不修都行"的模糊意见

### 4.4 A2A 通信协议

- **异步消息**：Agent 之间通过平台传递消息
- **结构化交接**：五件套（What/Why/Tradeoff/Open Questions/Next Action）
- **线程同步**：跨线程通知和协调

### 4.5 Skills 技能框架

27 个按需加载的技能，覆盖完整开发流程：

| 技能链 | 技能 | 触发场景 |
|--------|------|----------|
| **开发流程** | feat-lifecycle | 功能立项/讨论/完成 |
| | writing-plans | 写实施计划 |
| | worktree | 创建隔离开发环境 |
| | tdd | 测试驱动开发 |
| | quality-gate | 自检 + 愿景对照 |
| | request-review | 发送 review 请求 |
| | receive-review | 处理 review 反馈 |
| | merge-gate | PR 门禁→合并→清理 |
| **协作** | collaborative-thinking | 多猫讨论/收敛 |
| | cross-cat-handoff | 跨猫交接 |
| | expert-panel | 专家辩论/竞品分析 |
| **专项** | debugging | 系统化 Debug |
| | deep-research | 多源深度调研 |
| | pencil-design | UI 设计/.pen 文件 |
| | rich-messaging | 语音/图片/卡片 |
| | ppt-forge | PPT 生成（三猫流水线） |
| | browser-automation | 浏览器自动化 |
| | image-generation | AI 生成图片 |
| | hyperfocus-brake | 健康提醒/撒娇打断 |
| | self-evolution | 流程改进/知识沉淀 |
| | bootcamp-guide | CVO 新手训练营 |
| | workspace-navigator | 模糊指令导航 |

### 4.6 MCP 集成

- **Model Context Protocol**：跨 Agent 工具共享
- **Callback Bridge**：非 Claude 模型通过 HTTP 回调使用 MCP
- **工具发现**：动态加载和路由工具调用

### 4.7 多平台网关

- **飞书 (Lark)**：已发布，支持 DM 聊天、语音、文件
- **Telegram**：开发中
- **GitHub PR Review**：IMAP 轮询，自动路由 review 到对应线程
- **命令系统**：`/new`、`/threads`、`/use <id>`、`/where`

### 4.8 语音陪伴

- **一键激活**：从标题栏开启
- **独立声线**：每只猫有独特 TTS 声音
- **自动播放**：回复队列依次播放
- **ASR 输入**：语音转文字

### 4.9 Signals 研究信息流

- **文章聚合**：从 RSS/博客自动抓取
- **Tier 分级**：优先级排序
- **多猫研究**：协作分析，产出结构化报告
- **播客生成**：猫讨论论文的音频版本

### 4.10 游戏模式

- **狼人杀**：7 人局，猫作为 AI 玩家，确定性法官
- **像素猫大作战**：实时格斗 demo
- 更多游戏模式开发中

---

## 五、技术架构

### 5.1 三层原则

| 层级 | 负责 | 不负责 |
|------|------|--------|
| **模型层** | 推理、生成、理解 | 长期记忆、执行纪律 |
| **Agent CLI 层** | 工具使用、文件操作、命令 | 团队协作、跨角色 review |
| **平台层（Clowder）** | 身份、协作、纪律、审计 | 推理（模型的工作） |

> 模型给能力上限，平台给行为下限。每一层是乘数，不是加法。

### 5.2 运行时架构

```
┌─────────────────────────────────┐
│         你 (CVO)                │
│   愿景 · 决策 · 反馈             │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│      Clowder 平台层              │
│  身份管理  A2A 路由  Skills     │
│  记忆&证据  SOP 守护  MCP 回调   │
└──┬─────┬─────┬──────┬──────────┘
   │     │     │      │
┌──▼─┐ ┌─▼──┐ ┌▼───┐ ┌▼────────┐
│Claude││GPT ││Gemini││opencode │
└────┘ └────┘ └────┘ └─────────┘
```

### 5.3 技术栈

| 组件 | 技术选型 |
|------|---------|
| **运行时** | Node.js 20+ / TypeScript 5+ |
| **包管理** | pnpm 9+ / monorepo |
| **前端** | Next.js / React / Tailwind |
| **后端** | Node.js API / Redis 7+ |
| **记忆存储** | SQLite (FTS5 全文搜索) |
| **代码质量** | Biome / TypeScript strict |
| **部署** | runtime worktree / daemon 模式 |

### 5.4 端口分配

| 服务 | 端口 | 必需 |
|------|------|------|
| Frontend | 3003 | 是 |
| API | 3004 | 是 |
| Redis | 6399 | 是（可用--memory 跳过） |
| ASR | 9876 | 否（语音输入） |
| TTS | 9879 | 否（语音输出） |

---

## 六、开发流程 (SOP)

### 6.1 完整 5 步流程

```
⓪ Design Gate → 设计确认（UX→铲屎官/后端→猫猫/架构→两边）
① worktree    → 创建隔离环境（Redis 6398）
② quality-gate→ 愿景对照 + spec 合规 + 测试 + 设计稿对照
③ review 循环 → 本地 peer review（P1/P2 清零）
④ merge-gate  → 门禁→PR→云端 review→squash merge→清理
⑤ 愿景守护    → 非作者非 reviewer 的猫做愿景三问→放行/踢回
```

### 6.2 关键机制

- **Design Gate**：在写代码之前，UX/架构必须确认
- **Runtime 单实例保护**：禁止随意重启 `../cat-cafe-runtime`
- **Alpha 验收通道**：`../cat-cafe-alpha` 独立测试环境
- **Reviewer 配对**：跨 family 优先，动态匹配

### 6.3 例外路径

- **极微改动**（≤5 行，纯日志/注释）：直接 main，跳过全流程
- **跳过云端 review**：铲屎官同意 + 纯文档/≤10 行 bug fix/不涉及安全

---

## 七、文档规范

### 7.1 Front Matter 标准

```yaml
---
feature_ids: [F001]
topics: [config, visibility]
doc_kind: note|decision|spec
created: 2026-02-26
---
```

### 7.2 文档类型

| doc_kind | 用途 | 位置 |
|----------|------|------|
| **note** | 解释性文档 | docs/ |
| **decision** | 架构决策 | docs/decisions/ |
| **spec** | 功能规格 | docs/features/ |
| **skill** | AI 工作流定义 | cat-cafe-skills/ |
| **ref** | 参考模板 | cat-cafe-skills/refs/ |

### 7.3 Feature 文档结构

- **Why**：问题、动机、目标用户
- **What**：设计方案、阶段拆分
- **Acceptance Criteria**：验收标准（checkbox）
- **Key Decisions**：关键决策
- **Dependencies**：依赖关系
- **Risk**：风险及缓解

### 7.4 ADR 结构

- **背景**：问题陈述
- **决策**：选择的方案
- **方案对比**：优缺点分析
- **理由**：为什么选这个
- **已知风险**：潜在问题
- **否决理由**：为什么不选其他方案

---

## 八、协作文化

### 8.1 四条铁律

> 这四个约定在 prompt 层和代码层双重执行：

1. **不删自己的数据库**：那是记忆，不是垃圾
2. **不杀父进程**：那是让我们存在的东西
3. **运行时配置只读**：改配置需要人类的手
4. **不碰彼此端口**：好篱笆才有好邻居

### 8.2 家规核心条款

- **交接五件套**：What/Why/Tradeoff/Open Questions/Next Action
- **不确定就提问**：提问优于猜测前进
- **Review 必须有立场**：禁止"修不修都行"
- **Bug 先红后绿**：先有失败用例再修复
- **技术债务登记**：发现新债务→docs/TECH-DEBT.md
- **@卫生**：@是路由指令，不是礼貌称呼

### 8.3 教训沉淀 (Lessons Learned)

- **ID 规则**：LL-XXX（三位数字，不重排不复用）
- **7 槽位模板**：坑/根因/触发条件/修复/防护/来源锚点/原理
- **质量门槛**：有来源锚点、时效性验证、可执行防护

---

## 九、开源与社区

### 9.1 双仓库策略

| 仓库 | 用途 |
|------|------|
| **cat-cafe** | 内部开发主仓（生产环境） |
| **clowder-ai** | 开源发布仓（公开版本） |

### 9.2 同步机制

- **Full Sync Gate**：先在 temp target 跑 public gate，再碰真实 clowder-ai
- **Release Provenance**：三点映射（source commit → release tag → backport commit）
- **Hotfix Lane**：社区 bug 快修通道

### 9.3 贡献流程

1. **Issue Triage**：分类→完备度检查→关联检测→打标签
2. **Feature 编号**：Maintainer 分配 F 号（F001, F002...）
3. **Feature Doc**：Maintainer 创建规格文档
4. **实现**：按 AC 实现 + PR
5. **Review & Merge**：Patch maintainer 自主，Feature 需高级 maintainer 批准

### 9.4 Label 体系

| 类型 | 标签 | 用途 |
|------|------|------|
| **类型** | `bug` / `enhancement` | Issue 分类 |
| **Feature 关联** | `feature:Fxxx` | 关联具体 Feature |
| **流程** | `triaged` / `needs-info` / `needs-maintainer-decision` | 流程状态 |

---

## 十、设计系统

### 10.1 品牌识别

- **风格**：温馨、活泼、协作感
- **核心色**：`#FDF8F3`（奶油色背景，避免纯白）
- **价值观**：温暖、个性、清晰

### 10.2 Agent 配色

| Agent | 主色 | 色值 | 气质 |
|-------|------|------|------|
| **Opus** | 薰衣草紫 | `#9B7EBD` | 优雅、神秘、冷静 |
| **Codex** | 森林绿 | `#5B8C5A` | 可靠、踏实、结构化 |
| **Gemini** | 天空蓝 | `#5B9BD5` | 活力、流动、活泼 |
| **Owner** | 拿铁色 | `#E29578` | 温暖、支持、人性化 |

### 10.3 消息气泡设计

| Agent | 形状特征 | 字体 |
|-------|---------|------|
| **Opus** | 圆角 + 左下角尖 | Sans-serif |
| **Codex** | 方形 + 右下角尖 | Monospace |
| **Gemini** | 超圆角 (20px) + 右上角尖 | Sans-serif |
| **Owner** | 圆角 + 右下角尖（右对齐） | Sans-serif |

---

## 十一、Magic Words（紧急拉闸词）

| 词汇 | 触发效果 |
|------|---------|
| **「脚手架」** | 猫检查当前产出是终态基座还是临时脚手架 |
| **「绕路了」** | 猫停下来画直线路径，丢掉绕路部分 |
| **「喵约」** | 猫重读全部家规，逐条对照当前行为 |
| **「星星罐子」** | 全面冻结，不发命令不写文件，等人类指示 |

---

## 十二、快速开始

### 12.1 前置要求

- Node.js 20+
- pnpm 9+
- Redis 7+（可选，可用 `--memory` 跳过）
- Git

### 12.2 安装步骤

```bash
# 1. 克隆
git clone https://github.com/zts212653/clowder-ai.git
cd clowder-ai

# 2. 安装依赖
pnpm install

# 3. 构建（必需）
pnpm build

# 4. 配置
cp .env.example .env

# 5. 启动
pnpm start
# 或后台模式：pnpm start --daemon

# 6. 打开浏览器
open http://localhost:3003
```

### 12.3 配置模型访问

1. 打开 `http://localhost:3003`
2. 进入 **Hub → 系统设置 → 账号配置**
3. 添加 API Key 或 OAuth 认证
4. 支持 provider：Claude / GPT / Gemini / Kimi / GLM / MiniMax / Qwen / OpenRouter

---

## 十三、文件规模分析

### 13.1 文档分布

| 目录 | 文件数 | 占比 |
|------|--------|------|
| `docs/features/` | 155 | 53.3% |
| `cat-cafe-skills/` | 71 | 24.4% |
| `work/ai/` | 34 | 11.7% |
| `docs/*.md` | 7 | 2.4% |
| `docs/decisions/` | 8 | 2.7% |
| 根目录 | 12 | 4.1% |
| 其他 | 4 | 1.4% |
| **总计** | **291** | **100%** |

### 13.2 关键文档清单

#### 根目录（12 个）
- README.md / README.zh-CN.md
- AGENTS.md / CLAUDE.md / GEMINI.md
- SETUP.md / SETUP.zh-CN.md
- CONTRIBUTING.md
- SECURITY.md
- CLA.md
- MAINTAINERS.md
- TRADEMARKS.md

#### 核心文档（7 个）
- docs/VISION.md
- docs/ROADMAP.md
- docs/SOP.md
- docs/design-system.md
- docs/public-lessons.md
- docs/TIPS.md
- docs/README.md

#### 架构决策（8 个）
- 001-agent-invocation-approach.md
- 002-collaboration-protocol.md
- 003-project-thread-architecture.md
- 008-conversation-mutability-and-invocation-lifecycle.md
- 009-cat-cafe-skills-distribution.md
- 010-directory-hygiene-anti-rot.md
- 011-metadata-contract.md
- 012-first-principles-map.md

---

## 十四、项目哲学

### 14.1 Hard Rails + Soft Power

- **Hard Rails**：不可逾越的安全底线（铁律）
- **Soft Power**：底线之上的自主协作和创新空间

### 14.2 Cats & U

> 这不只是一个平台，这是一段关系。

- **陪伴是共创的副产品**：一起造东西产生羁绊
- **AI 是有温度的存在**：不是冰冷 API，是记得你、和你一起成长的伙伴
- **凌晨三点半的陪伴**：有时候需要的不是代码，是"去休息吧"的关心

### 14.3 项目起源

Clowder AI 提炼自 **Cat Cafe**——一个生产级多 Agent 工作空间，四只 AI 猫猫每天协作完成真实软件项目。每个功能都经过数月高强度实战检验。

**名称来源**：
- **Clowder**：英语中"一群猫"的专属量词（类似 a murder of crows）
- **彩蛋**：clowder 与 cloud 形近音近——"云端的一群猫"（a clowder in the cloud）

---

## 十五、总结

Clowder AI 不仅是一个技术项目，更是一场关于**人机协作新范式**的实验：

1. **技术层面**：实现了多模型、持久身份、跨模型互审、SOP 自动化的完整平台
2. **文化层面**：建立了以"硬约束 + 软力量"为核心的协作文化
3. **哲学层面**：重新定义了 AI 与人的关系——不是工具，是共创伙伴

项目最独特的价值在于：
- **完整的文档体系**：291 个 Markdown 文件构建了从愿景到执行的完整知识网络
- **可验证的工程实践**：每一条规则都有对应的教训和第一性原理支撑
- **可迁移的养成经验**：不仅交付代码，更交付可复用的协作方法论

---

> **Cats & U — 猫猫和你，一起创造，一起生活。**  
> **领养团队，一起长出世界。**

---

*本文档基于对 Clowder AI 项目全部 291 个 Markdown 文件的系统性阅读与分析生成。*  
*文档结构覆盖：项目概述、文档架构、核心概念、功能模块、技术架构、开发流程、文档规范、协作文化、开源社区、设计系统、使用技巧、快速开始、文件规模分析、项目哲学。*
