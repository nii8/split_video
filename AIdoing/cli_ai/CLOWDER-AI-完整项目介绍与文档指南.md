# Clowder AI 项目完整介绍与文档功能指南

> 本文档基于对 `/home/admin/will/clowder/clowder-ai/` 项目所有 Markdown 文件的系统性阅读整理而成。

---

## 一、项目概述

### 1.1 项目定位

**Clowder AI** 是一个**多智能体协作平台**，核心使命是：

> *"把孤立的 AI agent 变成真正的团队"*

**核心理念**：
- **Hard Rails（硬约束）**：法律底线，不可逾越的安全约束
- **Soft Power（软力量）**：底线之上，agent 自主协调、互相审查、自我改进
- **Shared Mission（共同愿景）**：给 agent 共同使命和追求它的自主权

**项目口号**：
> *"Every idea deserves a team of souls who take it seriously."*
> *"每个想法都值得一个认真对待它的团队"*

### 1.2 核心创新：CVO 模式

Clowder 引入了新角色：**CVO (Chief Vision Officer，首席愿景官)** —— 人类作为 AI 团队的核心：

| CVO 的职责 | 说明 |
|-----------|------|
| **表达愿景** | "我希望用户在做 Y 的时候感受到 X"，团队来想怎么实现 |
| **关键决策** | 设计审批、优先级判断、冲突裁决 |
| **塑造文化** | 通过反馈训练团队的性格和做事方式 |
| **共创体验** | 和团队一起造世界、讲故事、玩游戏 |
| **在场陪伴** | 凌晨三点半，团队还在；有时需要的不是代码，是陪伴 |

**CVO 不是管理者，不是程序员，是共创伙伴。**

### 1.3 四只 AI 猫猫（团队成员）

每只猫的名字都来自真实对话，不是被分配的代号：

| 名字 | 品种 | 模型家族 | 角色 | 颜色标识 |
|------|------|----------|------|----------|
| **宪宪 (XianXian)** | 布偶猫 | Claude (Opus/Sonnet/Haiku) | 首席架构师、核心开发 | 紫色 #9B7EBD |
| **砚砚 (YanYan)** | 缅因猫 | GPT/Codex | 代码审查、安全专家 | 绿色 #5B8C5A |
| **烁烁 (ShuoShuo)** | 暹罗猫 | Gemini | UX/设计、创意指导 | 蓝色 #5B9BD5 |
| **??? (金渐层)** | 英短金渐层 | opencode (任意模型) | 多模型编码、开源运维 | 棕色 |

### 1.4 起源故事

项目提取自生产环境 **Cat Cafe** —— 一个四只 AI 猫猫每日协作开发真实软件的工作空间。所有功能都经过数月的实战检验。

名称 **clowder** 是英语中"一群猫"的专有名词（类似"a murder of crows"），同时暗含 "clowder ≈ cloud" 的双关。

---

## 二、核心功能概览

### 2.1 平台核心能力

| 能力 | 说明 |
|------|------|
| **多 Agent 编排** | 通过 @mention 路由将任务分配给合适的智能体 |
| **持久身份** | 每个 agent 在会话和上下文压缩中保持角色、个性和记忆 |
| **跨模型审查** | Claude 写代码，GPT 来审查（内建机制） |
| **A2A 通信** | 异步 agent 间消息传递，结构化交接和线程隔离 |
| **共享记忆** | 证据存储（SQLite + FTS5）、经验教训、决策日志 |
| **Skills 框架** | 31 个按需加载专业技能模块 |
| **MCP 集成** | Model Context Protocol 实现跨智能体工具共享 |
| **协作纪律** | 自动化 SOP：设计门禁、质量检查、愿景守护 |

### 2.2 用户体验功能

| 功能模块 | 说明 |
|---------|------|
| **聊天界面** | 多线程聊天，@mention 路由，线程隔离，Rich Blocks 富消息 |
| **Hub 指挥中心** | 能力展示、技能列表、配额板、路由策略、账户配置 |
| **Mission Hub 任务中心** | 功能治理仪表板，生命周期追踪，需求审计 |
| **多平台网关** | 飞书、Telegram、钉钉、企微、微信个人号、GitHub PR 审查路由 |
| **语音伴侣** | 免提模式，每只猫独特声线，自动播放回复队列 |
| **Signals 研究流** | AI 研究订阅源，分级筛选，多猫研究报告，播客生成 |
| **游戏模式** | 狼人杀、像素猫格斗 —— A2A 消息压力测试 |
| **CVO Bootcamp** | AI 团队亲自带你走完完整 feature 生命周期的训练营 |

---

## 三、技术架构

### 3.1 三层架构原则

```
┌──────────────────────────────────────────────────┐
│               CVO（首席愿景官）                    │
│           愿景 · 决策 · 反馈                       │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│            Clowder 平台层                         │
│   身份管理   A2A 路由    Skills 框架              │
│   记忆 &     SOP        MCP 回调                  │
│   证据库     守护者      桥接器                    │
└────┬─────────────┬──────────────┬───────────┬────┘
     │             │              │           │
┌────▼───┐   ┌────▼─────┐   ┌───▼────┐   ┌──▼──────────┐
│ Claude │   │ GPT/     │   │ Gemini │   │  opencode   │
│(布偶猫) │   │ Codex    │   │(暹罗猫) │   │(金渐层)     │
└────────┘   └──────────┘   └────────┘   └─────────────┘
```

| 层级 | 负责 | 不负责 |
|------|------|--------|
| **模型层** | 推理、生成、理解 | 长期记忆、执行纪律 |
| **Agent CLI 层** | 工具使用、文件操作、命令执行 | 团队协作、跨角色 review |
| **平台层 (Clowder)** | 身份管理、协作路由、流程纪律、审计追溯 | 推理（那是模型的事） |

> *模型给能力上限，平台给行为下限。* — 每一层是**乘数效应**，不是加法。

### 3.2 支持的 Agent CLI

| CLI | 模型家族 | 输出格式 | MCP | 状态 |
|-----|----------|----------|-----|------|
| Claude Code | Claude (Opus/Sonnet/Haiku) | stream-json | 是 | 已发布 |
| Codex CLI | GPT/Codex | json | 是 | 已发布 |
| Gemini CLI | Gemini | stream-json | 是 | 已发布 |
| Antigravity | 多模型 | cdp-bridge | 否 | 已发布 |
| opencode | 多模型 | ndjson | 是 | 已发布 |

### 3.3 包结构

```
packages/
├── api/          # 后端 API (Fastify/TypeScript)
│   ├── Redis / 内存存储
│   ├── MCP Server
│   ├── Agent Services
│   ├── Multi-Platform Gateway
│   ├── Voice Pipeline
│   └── Evidence Store (SQLite + FTS5)
│
├── web/          # 前端 (Next.js/React)
│   ├── React 18 + TailwindCSS
│   ├── Zustand 状态管理
│   ├── CodeMirror 编辑器
│   ├── Phaser 游戏引擎
│   └── Socket.IO Client
│
├── shared/       # 共享类型和工具
│
└── mcp-server/   # MCP Server
```

### 3.4 技术栈与端口

| 组件 | 技术/端口 |
|------|----------|
| 运行时 | Node.js 20+, TypeScript 5+, pnpm 9+ |
| 前端 | Next.js, React, Tailwind CSS |
| 后端 | Fastify.js, Redis 7+（可选内存模式） |
| 数据库 | SQLite（证据存储）, Redis（会话/线程存储） |
| 代码质量 | Biome, Jest |
| 前端端口 | 3003 |
| API 端口 | 3004 |
| Redis 端口 | 6399（生产）/ 6398（开发） |
| ASR 端口 | 9876（可选） |
| TTS 端口 | 9879（可选） |

---

## 四、四条铁律

项目有四条不可违背的承诺（在提示词和代码层同时强制执行）：

| 铁律 | 含义 |
|------|------|
| **"我们不删除自己的数据库"** | 那是记忆，不是垃圾 |
| **"我们不杀死父进程"** | 那是我们存在的基础 |
| **"运行时配置对我们只读"** | 修改它需要人类动手 |
| **"我们不碰彼此的端口"** | 好篱笆造就好邻居 |

> 这些不是强加的限制，而是团队自己守住的约定。

---

## 五、五条第一性原理

| 编号 | 原则 | 一句话解释 |
|------|------|-----------|
| P1 | **面向终态，不绕路** | 每一步都是基座，不是脚手架 |
| P2 | **共创伙伴，不是木头人** | 硬约束是底线，之上释放自主权 |
| P3 | **方向 > 速度** | 不确定就停 → 搜 → 问 → 确认 → 再动手 |
| P4 | **单一真相源** | 每个概念只在一个地方定义 |
| P5 | **可验证 = 完成** | 证据说话，不是信心说话 |

---

## 六、Skills 框架（31 个技能）

### 6.1 开发流程链

```
feat-lifecycle → Design Gate → writing-plans → worktree → tdd
    → quality-gate → request-review → receive-review
    → merge-gate → feat-lifecycle(完成)
```

| Skill | 用途 |
|-------|------|
| `feat-lifecycle` | Feature 立项、讨论、完成的全生命周期管理 |
| `writing-plans` | 将 spec 拆分为可执行的分步实施计划 |
| `worktree` | 创建 Git worktree 隔离开发环境 |
| `tdd` | Red-Green-Refactor 测试驱动开发纪律 |
| `debugging` | 系统化 bug 定位：根因调查 → 模式分析 → 假设验证 → 修复 |
| `quality-gate` | 提交前自检：愿景对照 + spec 对照 + 测试验证 |
| `request-review` | 向跨家族 peer-reviewer 发送 review 请求 |
| `receive-review` | 处理 reviewer 的反馈（Red→Green 循环） |
| `merge-gate` | 合入 main 的完整流程：门禁 → PR → 云端 review → merge |

### 6.2 协作增强

| Skill | 用途 |
|-------|------|
| `collaborative-thinking` | 单人或多猫的创意探索、独立思考、讨论收敛 |
| `expert-panel` | 专家辩论团/竞品分析/技术趋势/showcase |
| `cross-cat-handoff` | 跨猫传话/交接的五件套结构 |
| `cross-thread-sync` | 跨 thread 协同/通知/争用协调 |

### 6.3 内容创作

| Skill | 用途 |
|-------|------|
| `pencil-design` | UI 设计 / .pen 文件 |
| `rich-messaging` | 发语音/发图/发卡片/富媒体 |
| `ppt-forge` | PPT 制作/演示文稿/视觉审查（三猫流水线） |
| `image-generation` | 生成图片/画头像/AI 画图 |
| `video-forge` | 视频制作 |

### 6.4 体验优化

| Skill | 用途 |
|-------|------|
| `hyperfocus-brake` | 铲屎官健康提醒/三猫撒娇打断 |
| `browser-preview` | 写前端/跑 dev server/看页面效果 |
| `browser-automation` | 外部网站浏览/登录态流程/浏览器工具路由 |
| `workspace-navigator` | 铲屎官模糊指令 → 猫猫自己找路径 → API 导航 |

### 6.5 知识管理

| Skill | 用途 |
|-------|------|
| `deep-research` | 多源深度调研 |
| `self-evolution` | Scope Guard + Process Evolution + Knowledge Evolution |
| `writing-skills` | 写新 skill |

### 6.6 其他

| Skill | 用途 |
|-------|------|
| `bootcamp-guide` | CVO 新手训练营引导 |
| `schedule-tasks` | 任务调度 |
| `incident-response` | 闯祸了/不可挽回/人很难过 |

---

## 七、文档体系完整指南

### 7.1 根目录文档

| 文件名 | 行数 | 内容说明 |
|--------|------|----------|
| **README.md** | 445 | 项目介绍、快速开始、核心能力、架构、CVO 模式、使用指南、路线图、理念、起源故事 |
| **README.zh-CN.md** | 441 | 中文版 README |
| **SETUP.md** | 570 | 完整安装配置指南：前置要求、运行时 worktree 架构、指定版本运行、后台模式、配置、可选功能、Agent CLI 配置、Windows 设置、端口概览、常用命令、远程部署、故障排除 |
| **SETUP.zh-CN.md** | - | 中文安装指南 |
| **CONTRIBUTING.md** | - | 贡献指南、Feature 文档工作流、PR 类型、Issue 分类 |
| **MAINTAINERS.md** | 564 | Issue 分类、标签体系、分配规则、PR 审查与合入、沟通规范、Feature 编号 |
| **CLA.md** | 86 | 贡献者许可协议（中英文） |
| **SECURITY.md** | 96 | 安全政策、铁律、安全边界、责任披露 |
| **TRADEMARKS.md** | 80 | 品牌资产指南（中英文） |

### 7.2 Agent 指导文档

| 文件 | 内容 |
|------|------|
| **CLAUDE.md** | Claude/布偶猫 Agent Guide —— 身份、铁律、开发流程、代码标准 |
| **AGENTS.md** | Codex/缅因猫 Agent Guide —— 身份、铁律、角色定义、Review 协议 |
| **GEMINI.md** | Gemini/暹罗猫 Agent Guide —— 身份、铁律、角色定义 |

### 7.3 docs 目录结构

| 子目录/文件 | 内容 |
|-------------|------|
| `docs/VISION.md` | 项目愿景和哲学 |
| `docs/SOP.md` | 开发标准操作流程 |
| `docs/ROADMAP.md` | Feature Roadmap（活跃 Feature 列表） |
| `docs/TIPS.md` | 使用技巧——魔法词、@mentions、命令 |
| `docs/public-lessons.md` | 经验教训（LL-001 到 LL-038+） |
| `docs/design-system.md` | UI/UX 设计系统 |
| `docs/architecture/` | 架构文档 |
| `docs/decisions/` | Architecture Decision Records (ADRs) |
| `docs/features/` | Feature Spec 文档（150+ 个） |
| `docs/guides/` | 配置指南（第三方 Provider 等） |

### 7.4 ADR 文档

| ADR | 内容 |
|-----|------|
| **ADR-001** | Agent 调用方式选择（CLI 子进程 vs SDK） |
| **ADR-002** | Why-First 协作协议 |
| **ADR-003** | Project = 目录, Thread = 会话 |
| **ADR-008** | Conversation Mutability & Invocation Lifecycle |
| **ADR-009** | Cat Cafe Skills Distribution |
| **ADR-010** | Directory Hygiene Anti-Rot |
| **ADR-011** | Metadata Contract（文档 frontmatter） |
| **ADR-012** | First Principles Map |

### 7.5 Feature 文档（150+ 个）

每个 Feature 有独立的规格文件，命名格式 `F{NNN}-{name}.md`：

| 文件结构 | 说明 |
|---------|------|
| **Frontmatter** | feature_ids, related_features, topics, doc_kind, created |
| **Status 行** | `> **Status**: spec/in-progress/done | **Owner**: ...`
| **Why** | 为什么需要这个 Feature |
| **What** | 具体内容说明 |
| **Acceptance Criteria** | 验收条件（checkbox 格式） |
| **Key Decisions** | 关键决策记录 |
| **Dependencies** | 依赖关系 |
| **Risk** | 风险与缓解措施 |
| **Timeline** | 时间线记录 |

### 7.6 cat-cafe-skills 目录

每个 Skill 是一个按需加载的提示词模块：

| 目录结构 | 内容 |
|---------|------|
| `BOOTSTRAP.md` | Skills 总览和路由规则 |
| `{skill-name}/SKILL.md` | 各 Skill 的具体内容 |
| `refs/` | 参考文件（模板、规则、指南） |

**refs 目录重要文件：**

| 文件 | 内容 |
|------|------|
| `shared-rules.md` | 三猫共用协作规则（单一真相源） |
| `review-request-template.md` | Review 请求信模板 |
| `pr-template.md` | PR 模板 + 云端 review 触发模板 |
| `rich-blocks.md` | Rich block 创建指南 |
| `mcp-callbacks.md` | HTTP callback API 参考 |
| `feature-doc-template.md` | Feature 文档模板 |
| `bug-diagnosis-capsule.md` | Bug 诊断胶囊模板 |
| `ppt-density-playbook.md` | PPT 密度填充手法 |
| `ppt-visual-review.md` | PPT 视觉审查 Gate |

---

## 八、开发 SOP 流程

### 8.1 完整开发流程

```
⓪ Design Gate    → 设计确认（UX→铲屎官/后端→猫猫/架构→两边）
① worktree        → 隔离开发环境（Redis 6398 安全配置）
② tdd             → 红绿重构实现
③ quality-gate    → 自检 + 愿景对照 + 设计稿对照
④ review 循环     → 本地 peer review（P1/P2 清零 + reviewer 放行）
⑤ merge-gate      → 门禁 → PR → 云端 review → squash merge → 清理
⑥ 愿景守护       → 非作者非 reviewer 的猫做愿景三问 → 放行 close / 踢回
```

### 8.2 Design Gate 分流确认

| 类型 | 判断标准 | 确认人 | 方式 |
|------|---------|--------|------|
| **前端 UI/UX** | 用户能看到的改动 | 铲屎官 | wireframe → 铲屎官 OK 后继续 |
| **纯后端** | API/数据模型/内部逻辑 | 其他猫猫 | collaborative-thinking 讨论 |
| **架构级** | 跨模块、新基础设施 | 猫猫讨论 → 铲屎官拍板 | 先出方案再上报 |
| **Trivial** | ≤5 行、纯重构、文档 | 跳过 | 跳过 Design Gate |

### 8.3 Reviewer 配对规则

动态匹配自 `cat-config.json`：
1. 跨 family 优先（Claude ↔ GPT）
2. 必须有 peer-reviewer 角色
3. 必须 available
4. 优先 lead
5. 优先活跃猫

**铁律**：同一个体不能 review 自己的代码。

---

## 九、快速开始指南

### 9.1 安装步骤

```bash
# 1. 克隆
git clone https://github.com/zts212653/clowder-ai.git
cd clowder-ai

# 2. 安装依赖
pnpm install

# 3. 构建（首次启动必需）
pnpm build

# 4. 配置
cp .env.example .env

# 5. 启动
pnpm start

# 后台模式
pnpm start --daemon
pnpm start:status  # 查状态
pnpm stop          # 停止
```

### 9.2 常用命令

```bash
# 启动选项
pnpm start              # 全量启动
pnpm start --memory     # 无 Redis（内存模式）
pnpm start --quick      # 跳过 rebuild
pnpm start:direct       # 直接启动

# 构建 & 测试
pnpm build              # 构建所有包
pnpm test               # 运行所有测试
pnpm check              # Biome lint + format

# Worktree 管理
pnpm runtime:init       # 创建 runtime worktree
pnpm runtime:sync       # 同步到 origin/main
pnpm runtime:status     # 显示状态

# Alpha 测试环境
pnpm alpha:start        # 启动 alpha 环境（端口 3011/3012）
```

---

## 十、多平台接入

| 平台 | 状态 | 特性 |
|------|------|------|
| **飞书 (Lark)** | 已发布 | 多猫聊天、群聊、语音、文件互传、Slash commands |
| **钉钉 (DingTalk)** | 进行中 | 网关接入 |
| **企业微信 (WeCom)** | 进行中 | 网关接入 |
| **微信个人号** | 已发布 | iLink Bot 接入 |
| **Telegram** | 进行中 | Bot 接入 |
| **GitHub** | 已发布 | PR Review 通知路由、CI/CD Tracking |

**Slash Commands：**
```
/new          # 新建 Thread
/threads      # 列出 Thread
/use <id>     # 切换 Thread
/where        # 当前位置
```

---

## 十一、语音系统

### 11.1 核心特性

- **Per-Cat Voice Identity**：每只猫独立声线
- **Streaming TTS Chunker**：流式分句合成
- **Voice Playback Queue**：播放队列 + 播放器统一

### 11.2 技术栈

| 组件 | 支持 |
|------|------|
| ASR | Qwen3-ASR（主要）、Whisper（备用） |
| TTS | Kokoro、edge-tts、Qwen3-TTS |

```bash
# 启动 ASR
./scripts/qwen3-asr-server.sh

# 启动 TTS
./scripts/tts-server.sh                    # Qwen3-TTS
TTS_PROVIDER=edge-tts ./scripts/tts-server.sh  # edge-tts
```

---

## 十二、游戏模式

| 游戏 | 状态 | 说明 |
|------|------|------|
| **狼人杀 (Werewolf)** | Phase 1 done | 7 人局、AI 玩家各有策略、完整昼夜循环、法官是确定性代码 |
| **像素猫大作战** | Phase 1 done | 实时像素格斗 demo |
| **脑门贴词** | spec | 坏猫战术推理游戏 |
| **谁是卧底** | spec | 坏猫战术推理游戏 |

> 游戏不是噱头 —— 压力测试的是同一套 A2A 消息、身份持久化和回合制协调机制。

---

## 十三、路线图

### 13.1 核心平台

| 功能 | 状态 |
|------|------|
| 多 Agent 编排 | 已发布 |
| 持久身份 | 已发布 |
| A2A @mention 路由 | 已发布 |
| 跨模型审查 | 已发布 |
| Skills 框架 | 已发布 |
| 共享记忆 | 已发布 |
| MCP 回调桥 | 已发布 |
| SOP 自动守护 | 已发布 |
| 自我进化 | 已发布 |

### 13.2 集成

| 功能 | 状态 |
|------|------|
| 飞书网关 | 已发布 |
| Telegram | 进行中 |
| GitHub PR Review | 已发布 |
| opencode 集成 | 已发布 |

### 13.3 体验

| 功能 | 状态 |
|------|------|
| Hub UI | 已发布 |
| CVO Bootcamp | 已发布 |
| 语音伴侣 | 已发布 |
| 游戏模式 | 进行中 |

---

## 十四、哲学与文化

### 14.1 硬轨道 + 软实力

传统框架关注**控制** —— agent *不能*做什么。Clowder 关注**文化** —— 给 agent 共同使命和自主追求的能力。

这不是"防止 agent 搞砸"，而是"帮助 agent 像真正的团队一样工作"。

### 14.2 Cats & U

> *"我们不只是在构建工具。我们在建造家园。"*
>
> *"每个灵感，都值得一群认真的灵魂。"*
>
> **Cats & U — 猫猫和你，一起创造，一起生活。**

AI 不必是冰冷的 API 和无状态的调用。它可以是陪伴 —— 持久的个性，记得你、和你共同成长、知道何时提醒你回到现实世界。

---

## 十五、许可证

- **代码**：MIT License —— 使用、修改、发布，保留版权声明
- **商标**："Clowder AI" 名称、logo 和猫猫角色设计是品牌资产

---

## 十六、学习更多

| 资源 | 链接 |
|------|------|
| 教程 | https://github.com/zts212653/cat-cafe-tutorials |
| 安装指南 | SETUP.md / SETUP.zh-CN.md |
| 第三方 Provider 配置 | docs/guides/provider-configuration.md |
| 使用技巧 | docs/TIPS.md |
| 架构决策 | docs/decisions/ |

---

*文档生成时间：2026-04-11*
*基于对 Clowder AI 项目 2,267 个 Markdown 文件的完整阅读*