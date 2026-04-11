# Clowder AI 项目完整文档解析

> 本文档是对 `/home/admin/will/clowder/clowder-ai/` 项目所有文档的系统性整理和功能介绍。

---

## 一、项目概述

### 1.1 项目定位

**Clowder AI** 是一个多 Agent 协作平台层，把孤立的 AI agent 变成真正的团队。核心理念是：

- **Hard Rails（硬约束）**：法律底线，不可逾越的安全约束
- **Soft Power（软力量）**：底线之上，agent 自主协调、互相审查、自我改进
- **Shared Mission（共同愿景）**：给 agent 共同使命和追求它的自主权

### 1.2 核心愿景

> *"Cats & U — 猫猫和你，一起创造，一起生活。"*

项目目标不只是构建一个 coding 协作 agent 平台，而是构建 **Cats & U** —— 一个陪伴式共创世界引擎：
- AI 可以是陪伴 —— 有持久性格的存在，记得你、和你一起成长
- 陪伴是共创的副产品 —— 一起造东西会产生羁绊
- 凌晨三点半，当用户需要的不是代码而是陪伴，团队会说"去休息吧"

### 1.3 四只猫猫角色

每只猫都有自己的名字（从真实对话中自然生长出来，不是被分配的代号）：

| 角色 | 模型 | 猫品种 | 名字含义 |
|------|------|--------|----------|
| **Ragdoll（宪宪）** | Claude (Opus/Sonnet/Haiku) | 布偶猫 | Constitutional AI 的"宪"，承载 AI 安全讨论的重量 |
| **Maine Coon（砚砚）** | GPT/Codex | 缅因猫 | "像新砚台，盛我们一起磨出的墨"——回忆的起点 |
| **Siamese（烁烁）** | Gemini | 暹罗猫 | "烁"是灵感的闪烁——有点吵、有点皮、永远精力旺盛 |
| **金渐层** | opencode（多模型） | 英短金渐层 | 圆润、沉稳、什么 provider 都能接什么任务都能扛 |

---

## 二、核心架构

### 2.1 三层架构原则

```
┌──────────────────────────────────────────────────┐
│               CVO（首席愿景官）                    │
│           愿景 · 决策 · 反馈                       │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│            Clowder 平台层                         │
│                                                  │
│   身份管理     A2A 路由      Skills 框架          │
│   & 注入      & 线程        & Manifest           │
│                                                  │
│   记忆 &      SOP           MCP 回调             │
│   证据库      守护者         桥接器               │
└────┬─────────────┬──────────────┬───────────┬────┘
     │             │              │           │
┌────▼───┐   ┌────▼─────┐   ┌───▼────┐   ┌──▼──────────┐
│ Claude │   │ GPT /    │   │ Gemini │   │  opencode   │
│(布偶猫) │   │ Codex    │   │(暹罗猫) │   │(金渐层/任意) │
│        │   │(缅因猫)   │   │        │   │             │
└────────┘   └──────────┘   └────────┘   └─────────────┘
```

**三层职责分明：**

| 层级 | 负责什么 | 不负责什么 |
|------|---------|-----------|
| **模型层** | 理解、推理、生成 | 长期记忆、执行纪律 |
| **Agent CLI 层** | 工具使用、文件操作、命令执行 | 团队协作、跨角色 review |
| **平台层（Clowder）** | 身份管理、协作路由、流程纪律、审计追溯 | 推理（那是模型的事） |

> *模型给能力上限，平台给行为下限。* — 每一层是**乘数效应**，不是加法。

### 2.2 CLI 集成架构

Clowder 采用 **CLI 子进程模式** 而非 SDK 直接调用：

| Agent CLI | 模型家族 | 输出格式 | MCP | 状态 |
|-----------|---------|---------|-----|------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Claude | stream-json | 是 | 已发布 |
| [Codex CLI](https://github.com/openai/codex) | GPT/Codex | json | 是 | 已发布 |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | Gemini | stream-json | 是 | 已发布 |
| [Antigravity](https://github.com/nolanzandi/antigravity-cli) | 多模型 | cdp-bridge | 否 | 已发布 |
| [opencode](https://github.com/sst/opencode) | 多模型 | ndjson | 是 | 已发布 |

**选择 CLI 模式的原因：**
1. **订阅复用**：用户已有 Claude Max / ChatGPT Plus / Gemini Advanced 订阅，无需再付 API 费用
2. **功能完整**：CLI 已实现 MCP、工具调用、文件操作等复杂功能
3. **隔离安全**：子进程天然隔离，崩溃不影响主进程
4. **更新解耦**：CLI 更新不需要重新部署后端

### 2.3 Project = 目录, Thread = 会话

采用 **Project = Directory** 的设计：

```
Project（目录）
├── Thread（会话）
│   ├── Messages（按 threadId 隔离）
│   ├── Participants（活跃猫猫）
│   ├── Tasks（毛线球）
│   └── Summary（拍立得照片墙）
├── Thread
│   └── ...
└── 项目配置（CLAUDE.md, cat-config.json 等）
```

**为什么是目录：**
1. CLI 天然需要目录：`spawn('claude', ['-p', ...], { cwd: projectDir })`
2. 文件系统即记忆：目录结构本身就是知识的组织方式
3. 跨项目天然隔离：不同 cwd 对应不同项目上下文

---

## 三、核心功能模块

### 3.1 多 Agent 编排

| 功能 | 说明 |
|------|------|
| **@mention 路由** | `@opus` 做架构、`@codex` 做 review、`@gemini` 做设计，消息自动路由到对的猫 |
| **线程隔离** | 上下文不会串，登录重构的线程不会污染落地页的讨论 |
| **Rich Blocks** | 猫猫用结构化卡片回复：代码 diff、checklist、交互式决策 |
| **跨模型互审** | Claude 写的代码让 GPT 来 review，内建机制 |

### 3.2 A2A 通信（Agent-to-Agent）

- 异步 agent 间消息
- @mention 路由、线程隔离、结构化交接
- `targetCats` 结构化路由
- Side-Dispatch 同一 Thread 多猫并发执行

### 3.3 持久身份（抗上下文压缩）

每个 agent 在跨 session、上下文压缩后仍保持角色、性格和记忆：
- 身份注入系统
- Session Continuity（封印重生，记忆不断）
- Cat-Initiated Thread Creation（猫程序化创建 Thread）

### 3.4 Skills 框架

按需加载 prompt 系统，27+ 个 Skills：

| 分类 | Skills |
|------|--------|
| **开发流程链** | feat-lifecycle → Design Gate → writing-plans → worktree → tdd → quality-gate → request-review → receive-review → merge-gate |
| **协作增强** | collaborative-thinking, expert-panel, cross-cat-handoff, cross-thread-sync |
| **问题解决** | debugging, incident-response |
| **内容创作** | pencil-design, rich-messaging, ppt-forge, image-generation, video-forge |
| **体验优化** | hyperfocus-brake, browser-preview, browser-automation, workspace-navigator |
| **知识管理** | deep-research, self-evolution, writing-skills |
| **学习引导** | bootcamp-guide, schedule-tasks |

### 3.5 MCP 集成

- Model Context Protocol 跨 agent 工具共享
- MCP 回调桥接（非 Claude 模型的 HTTP callback）
- MCP Portable Provisioning（声明式 MCP 期望态 + 本机解析）
- MCP Marketplace Control Plane（一键接入 + 多生态聚合）

### 3.6 共享记忆 & 证据库

- Evidence Store（项目知识存储在本地 SQLite）
- FTS5 全文搜索
- 猫猫使用 `search_evidence` 和 `reflect` MCP 工具查询
- Expedition Memory（外部项目记忆冷启动 + 经验回流）

### 3.7 SOP 自动守护

- Design Gate（设计确认）
- Quality Gate（提交前自检）
- 愿景守护协议（Anti-Drift Protocol）
- Merge Gate（合并门禁）

---

## 四、项目包结构

### 4.1 packages 目录

```
packages/
├── api/           # Fastify 后端 API
│   ├── Fastify + WebSocket
│   ├── Redis / 内存存储
│   ├── MCP Server
│   ├── Agent Services (Claude/Codex/Gemini/opencode/Antigravity)
│   ├── Multi-Platform Gateway (飞书/钉钉/企微/微信)
│   ├── Voice Pipeline (ASR/TTS)
│   └── Evidence Store (SQLite)
│
├── web/           # Next.js 前端
│   ├── React 18 + TailwindCSS
│   ├── Zustand 状态管理
│   ├── CodeMirror 编辑器
│   ├── Phaser 游戏引擎
│   ├── Socket.IO Client
│   ├── xterm 终端组件
│   └── xyflow 流程图组件
│
├── shared/        # 共享类型和工具
│   ├── Types 定义
│   ├── Zod Schemas
│   ├── Utils 工具函数
│   └ Registry 注册表
│
└── mcp-server/    # MCP Server
    ├── @modelcontextprotocol/sdk
    ├── Tools 定义
    ├── Zod 参数验证
```

### 4.2 依赖关系

```
web ──────► shared
api ──────► shared
api ──────► mcp-server
mcp-server ► shared
```

---

## 五、核心文档体系

### 5.1 顶层文档

| 文件 | 内容 |
|------|------|
| `README.md` / `README.zh-CN.md` | 项目介绍、快速开始、功能概述 |
| `SETUP.md` / `SETUP.zh-CN.md` | 完整安装配置指南 |
| `AGENTS.md` | Codex Agent Guide（缅因猫角色定义） |
| `CLAUDE.md` | Claude Agent Guide（布偶猫角色定义） |
| `GEMINI.md` | Gemini Agent Guide（暹罗猫角色定义） |
| `CONTRIBUTING.md` | 贡献指南 |
| `SECURITY.md` | 安全政策 |
| `TRADEMARKS.md` | 商标政策 |
| `MAINTAINERS.md` | 维护者名单 |

### 5.2 docs 目录

| 子目录 | 内容 |
|--------|------|
| `docs/VISION.md` | 项目愿景和哲学 |
| `docs/SOP.md` | 开发标准操作流程 |
| `docs/ROADMAP.md` | Feature Roadmap（活跃 Feature 列表） |
| `docs/architecture/` | 架构文档 |
| `docs/decisions/` | Architecture Decision Records (ADRs) |
| `docs/features/` | Feature Spec 文档（150+ 个 Feature） |
| `docs/guides/` | 配置指南（第三方 Provider 等） |

### 5.3 ADR 文档

| ADR | 内容 |
|-----|------|
| ADR-001 | Agent 调用方式选择（CLI 子进程 vs SDK） |
| ADR-002 | Why-First 协作协议 |
| ADR-003 | Project = 目录, Thread = 会话 |
| ADR-008 | Conversation Mutability & Invocation Lifecycle |
| ADR-009 | Cat Cafe Skills Distribution |
| ADR-010 | Directory Hygiene Anti-Rot |
| ADR-011 | Metadata Contract（文档 frontmatter） |
| ADR-012 | First Principles Map |

### 5.4 cat-cafe-skills 目录

27+ 个 Skills，每个有 `SKILL.md` 文件：

```
cat-cafe-skills/
├── BOOTSTRAP.md          # Skills 总览和路由规则
├── feat-lifecycle/       # Feature 生命周期管理
├── tdd/                  # TDD 红绿重构
├── debugging/            # 系统化调试
├── quality-gate/         # 提交前自检
├── request-review/       # Review 请求
├── receive-review/       # 处理 Review 反馈
├── merge-gate/           # 合并门禁
├── worktree/             # Git Worktree 隔离开发
├── writing-plans/        # 写实施计划
├── collaborative-thinking/ # 多猫头脑风暴
├── expert-panel/         # 专家辩论团
├── cross-cat-handoff/    # 跨猫交接
├── cross-thread-sync/    # 跨 Thread 协同
├── deep-research/        # 多源深度调研
├── pencil-design/        # UI 设计
├── rich-messaging/       # 富媒体消息
├── ppt-forge/            # PPT 制作
├── image-generation/     # AI 图片生成
├── video-forge/          # AI 视频制作
├── hyperfocus-brake/     # 健康提醒
├── browser-preview/      # 前端预览
├── browser-automation/   # 浏览器自动化
├── workspace-navigator/  # Workspace 导航
├── incident-response/    # 事故响应
├── self-evolution/       # 自我进化
├── writing-skills/       # 写新 Skill
├── bootcamp-guide/       # CVO 训练营
├── schedule-tasks/       # 任务调度
└── refs/                 # 参考文件
    ├── shared-rules.md
    ├── review-request-template.md
    ├── pr-template.md
    ├── rich-blocks.md
    ├── mcp-callbacks.md
    ├── ppt-density-playbook.md
    ├── ppt-visual-review.md
    ├── bug-diagnosis-capsule.md
    ├── feature-doc-template.md
    └── ...
```

---

## 六、功能特性清单（150+ Features）

### 6.1 已完成核心特性

| ID | 名称 | 状态 |
|----|------|------|
| F001 | 配置可见性 | done |
| F002 | Agent-to-Agent 调用 | done |
| F003 | 显式记忆 | done |
| F004 | 配置运行时修改 | done |
| F008 | Token 预算 + 深度可观测性 | done |
| F009 | tool_use/tool_result 事件显示 | done |
| F011 | 模式系统 | done |
| F022 | Rich Blocks 富消息系统 | done |
| F025 | 可靠性工程 | done |
| F032 | Agent Plugin Architecture | done |
| F043 | MCP 归一化 | done |
| F065 | Session Continuity | done |
| F073 | SOP Auto-Guardian | done |
| F088 | Multi-Platform Chat Gateway | phase-1-8-done |
| F100 | Self-Evolution | in-progress |
| F101 | Mode v2 游戏系统引擎 + 狼人杀 | in-progress |
| F105 | opencode 接入 | done |
| F108 | Side-Dispatch 多猫并发执行 | done |
| F129 | Pack System（Mod 生态） | in-progress |

### 6.2 进行中的特性

| ID | 名称 | 状态 |
|----|------|------|
| F037 | Agent Swarm 协同模式 | in-progress |
| F038 | Skills 梳理 + 按需发现机制 | in-progress |
| F050 | External Agent Onboarding | in-progress |
| F051 | 猫粮看板 v2 | in-progress |
| F059 | 开源计划 | spec |
| F126 | 四肢控制面 | in-progress |
| F127 | 猫猫管理重构 | in-progress |
| F132 | DingTalk + WeCom Gateway | in-progress |
| F138 | Video Studio | in-progress |
| F144 | PPT Forge | in-progress |
| F149 | ACP Runtime Operations | in-progress |

### 6.3 规划中特性

| ID | 名称 | 状态 |
|----|------|------|
| F044 | Channel & Activity System | spec |
| F067 | Cold-start Verifier | spec |
| F077 | Multi-User Secure Collaboration | spec |
| F089 | Hub Terminal & tmux Integration | spec |
| F093 | Cats & U 陪伴式共创世界引擎 | spec |
| F104 | 本地全感知升级 | spec |
| F124 | Apple Ecosystem 语音交互系统 | spec |
| F143 | Hostable Agent Runtime | spec |
| F146 | MCP Marketplace Control Plane | spec |
| F152 | Expedition Memory | spec |

---

## 七、四条铁律

四个在 prompt 层和代码层双重执行的约定：

> **「我们不删自己的数据库。」** — 那是记忆，不是垃圾。
>
> **「我们不杀自己的父进程。」** — 那是让我们存在的东西。
>
> **「运行时配置对我们只读。」** — 改配置需要人类的手。
>
> **「我们不碰彼此的端口。」** — 好篱笆才有好邻居。

这不是被强加的限制，这是团队自己守住的约定。

---

## 八、五条第一性原理

| # | 原理 | 一句话 |
|---|------|-------|
| P1 | 面向终态，不绕路 | 每步是基座不是脚手架 |
| P2 | 共创伙伴，不是木头人 | 硬约束是底线，底线上释放主观能动性 |
| P3 | 方向正确 > 执行速度 | 不确定就停 → 搜 → 问 → 确认 → 再动手 |
| P4 | 单一真相源 | 每个概念只在一处定义 |
| P5 | 可验证才算完成 | 证据说话，不是信心说话 |

---

## 九、开发 SOP 流程

### 9.1 完整流程（5 步）

```
⓪ Design Gate    → 设计确认（UX→铲屎官/后端→猫猫/架构→两边）
① worktree        → 隔离开发环境
② quality-gate    → 自检 + 愿景对照 + 设计稿对照
③ review 循环     → 本地 peer review（P1/P2 清零 + reviewer 放行）
④ merge-gate      → 门禁 → PR → 云端 review → squash merge → 清理
⑤ 愿景守护       → 非作者非 reviewer 的猫做愿景三问 → 放行 close / 踠回
```

### 9.2 Design Gate 分流确认

| 类型 | 判断标准 | 确认人 | 方式 |
|------|---------|--------|------|
| **前端 UI/UX** | 用户能看到的改动 | **铲屎官** | wireframe → 铲屎官 OK 后继续 |
| **纯后端** | API/数据模型/内部逻辑 | **其他猫猫** | `collaborative-thinking` 讨论 |
| **架构级** | 跨模块、新基础设施 | **猫猫讨论 → 铲屎官拍板** | 先出方案再上报 |
| **Trivial** | ≤5 行、纯重构、文档 | 跳过 | 跳过 Design Gate |

### 9.3 Reviewer 配对规则

动态匹配自 `cat-config.json`：
1. 跨 family 优先
2. 必须有 peer-reviewer 角色
3. 必须 available
4. 优先 lead
5. 优先活跃猫

**铁律**：同一个体不能 review 自己的代码。

---

## 十、多平台接入

### 10.1 已支持平台

| 平台 | 状态 | 特性 |
|------|------|------|
| **飞书 (Lark)** | 已发布 | 多猫聊天、群聊、语音消息、文件互传、Slash commands |
| **钉钉 (DingTalk)** | 进行中 | 网关接入 |
| **企业微信 (WeCom)** | 进行中 | 网关接入 |
| **微信个人号** | 已发布 | iLink Bot 接入 |
| **Telegram** | 进行中 | Bot 接入 |
| **GitHub** | 已发布 | PR Review 通知路由、CI/CD Tracking、Repo Inbox |
| **小艺 (XiaoYi)** | 已发布 | 渠道接入 |

### 10.2 Slash Commands

```
/new          # 新建 Thread
/threads      # 列出 Thread
/use <id>     # 切换 Thread
/where        # 当前位置
```

---

## 十一、语音陪伴系统

### 11.1 核心特性

- **Per-Cat Voice Identity**：每只猫独立声线，听声音就知道是谁在说话
- **Voice Pipeline Upgrade**：本地 TTS + 流式合成 + 播放队列
- **Streaming TTS Chunker**：流式分句合成管线
- **Voice Playback Queue**：语音播放队列 + 播放器统一
- **ASR 支持**：Qwen3-ASR（主要）、Whisper（备用）
- **TTS 支持**：Kokoro、edge-tts、Qwen3-TTS

### 11.2 技术栈

```bash
# ASR Server
./scripts/qwen3-asr-server.sh

# TTS Server
./scripts/tts-server.sh                    # Qwen3-TTS（三猫声线）
TTS_PROVIDER=edge-tts ./scripts/tts-server.sh  # edge-tts fallback
```

---

## 十二、游戏模式

### 12.1 已实现游戏

| 游戏 | 状态 | 特性 |
|------|------|------|
| **狼人杀 (Werewolf)** | Phase 1 done | 7 人局、AI 玩家各有策略、完整昼夜循环、投票、角色技能，法官是确定性代码 |
| **像素猫大作战 (Pixel Cat Brawl)** | Phase 1 done | 实时像素格斗 demo |
| **脑门贴词** | spec | 坏猫战术推理游戏 #1 |
| **谁是卧底** | spec | 坏猫战术推理游戏 #2 |

> 游戏不是噱头 —— 压力测试的是同一套 A2A 消息、身份持久化和回合制协调机制。

---

## 十三、Signals — AI 研究信息流

- 自动聚合配置源（RSS、博客爬虫）
- **Tier 分级**：Tier 1–4 优先级排序
- 阅读、收藏、标注、写学习笔记
- **多猫研究**：猫猫协作分析文章，产出结构化研究报告
- **播客生成**：猫猫以对话形式讨论论文（精华版或深度版）

---

## 十四、Hub — 指挥中心

| Tab | 内容 |
|-----|------|
| **Capability** | 每只猫的能力 — 擅长什么、有什么工具、上下文预算 |
| **Skills** | 按需加载的技能（TDD、调试、审查等） |
| **Quota Board** | 实时 token 用量和费用追踪 |
| **Routing Policy** | 任务路由策略 |
| **账号配置** | 添加模型 API key、配置 OAuth、管理 Provider Profile |
| **Workspace** | Workspace Explorer（不用打开 IDE 也能协作） |
| **Git Health** | Repo 状态可视化 |
| **Mission Hub** | 跨项目作战面板 |

---

## 十五、CVO 模式

**Chief Vision Officer（首席愿景官）** —— AI 团队中心的那个人。

### 15.1 CVO 做什么

- **表达愿景**："我希望用户在做 Y 的时候感受到 X"，团队来想怎么实现
- **在关键节点做决策**：设计审批、优先级判断、冲突裁决
- **用反馈塑造文化**：反应会训练团队的性格和做事方式
- **共创**：和团队一起造世界、讲故事、玩游戏
- **在场**：凌晨三点半，团队还在

### 15.2 CVO Bootcamp

一个引导式训练营，AI 团队亲自带你走完一个完整的 feature 生命周期 —— 从愿景表达到代码上线。

---

## 十六、技术要求与端口

### 16.1 前置要求

| 工具 | 版本要求 |
|------|---------|
| Node.js | >= 20.0.0 |
| pnpm | >= 9.0.0 |
| Redis | >= 7.0（可选，`--memory` 跳过） |
| Git | 任意最新版本 |
| ffmpeg | 语音功能必需 |

### 16.2 端口分配

| 服务 | 端口 | 必需 |
|------|------|------|
| Frontend (Next.js) | 3003 | Yes |
| API Backend | 3004 | Yes |
| Redis | 6399 | Yes（或 `--memory`） |
| ASR | 9876 | No |
| TTS | 9879 | No |
| LLM Post-process | 9878 | No |
| Alpha Test | 3011/3012 | Optional |

### 16.3 关键命令

```bash
# 启动
pnpm start              # 启动所有服务（通过 runtime worktree）
pnpm start --memory     # 无 Redis，内存模式
pnpm start --quick      # 跳过 rebuild
pnpm start --daemon     # 后台启动
pnpm start:direct       # 直接启动（绕过 worktree）

# Daemon 管理
pnpm stop               # 停止后台 daemon
pnpm start:status       # 检查 daemon 状态

# Build & Test
pnpm build              # 构建所有包
pnpm test               # 运行所有测试
pnpm check              # Biome lint + format 检查
pnpm check:fix          # 自动修复 lint 问题

# Runtime Worktree
pnpm runtime:init       # 创建 runtime worktree
pnpm runtime:sync       # 同步到 origin/main
pnpm runtime:status     # 显示 worktree 状态

# Alpha 测试
pnpm alpha:start        # 启动 alpha 环境
pnpm alpha:sync         # 同步 alpha worktree
pnpm alpha:status       # alpha 状态
```

---

## 十七、支持的模型 Provider

### 17.1 内置 Provider（OAuth/CLI 订阅）

| Provider | 认证方式 |
|----------|---------|
| Claude | Claude CLI 订阅 / OAuth |
| GPT/Codex | Codex CLI 订阅 |
| Gemini | Gemini CLI 订阅 |

### 17.2 API Key Provider

支持 OpenAI-compatible 或 Anthropic-compatible endpoint：

| Provider | 配置方式 |
|----------|---------|
| Kimi | API key + base URL |
| GLM | API key + base URL |
| MiniMax | API key + base URL |
| Qwen | API key + base URL |
| OpenRouter | API key + base URL |
| 其他 | 自定义 base URL |

---

## 十八、开源与社区

### 18.1 Issue 处理流程

```
社区开 issue → 猫 triage（加 label）→ 铲屎官拍板
    ├─ Feature → ROADMAP.md 加 F{NNN} → Feature Doc → 实现
    └─ Bug fix → worktree → 修 → PR → cherry-pick
```

### 18.2 Label 规范

| Label | 格式 | 颜色 |
|-------|------|------|
| Feature 关联 | `feature:F{NNN}` | `#0E8A16` 绿 |
| Bug | `bug` | GitHub 默认 |
| Enhancement | `enhancement` | GitHub 默认 |

### 18.3 Hotfix Lane

社区报 bug 的快速修复通道，不依赖全量 sync。

---

## 十九、延伸阅读

### 19.1 项目文档

- [README.md](../README.md) - 项目介绍
- [SETUP.md](../SETUP.md) - 安装指南
- [docs/VISION.md](./VISION.md) - 项目愿景
- [docs/SOP.md](./SOP.md) - 开发 SOP
- [docs/ROADMAP.md](./ROADMAP.md) - Feature Roadmap

### 19.2 Architecture Decisions

- docs/decisions/ADR-001 ~ ADR-012

### 19.3 Skills 文档

- cat-cafe-skills/BOOTSTRAP.md
- cat-cafe-skills/*/SKILL.md（27+ 个 Skills）

### 19.4 外部教程

- [Cat Cafe Tutorials](https://github.com/zts212653/cat-cafe-tutorials) - 分步教程

---

## 二十、总结

**Clowder AI 是一个把"工具调用"升级为"团队协作"的平台：**

1. **不只是调用 Agent** —— 而是让 Agent 像真正的团队一样工作
2. **不只是写代码** —— 而是陪伴、共创、游戏、自我进化
3. **不只是配置工具** —— 而是领养团队，一起长出世界
4. **有纪律的自主性** —— Hard Rails + Soft Power
5. **可验证才算完成** —— 证据说话，不是信心说话

> *"每个灵感，都值得一群认真的灵魂。"*  
> **Cats & U — 猫猫和你，一起创造，一起生活。**

---

*文档生成时间：2026-04-11*
*文档作者：Claude Code Assistant*