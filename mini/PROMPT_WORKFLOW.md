# 提示词工作流

这几个文件的用途不同，不要混用。

## 1. `START_PROMPT.md`

用于：

- 新开会话
- 恢复上下文
- 防止默认全量扫描文档

作用：

- 固定项目根目录
- 固定文档读取顺序
- 固定“最新任务”判定规则

## 2. `CODEX_LOOP_PROMPT.md`

用于：

- 你对 Codex 的固定循环口令
- 每一轮继续推进主线时反复使用

作用：

- 让 Codex 自动读取最新核心文档和最新任务
- 自动决定写代码、写任务还是分析结果
- 用固定摘要格式输出

## 3. `OPENCODE_LOOP_PROMPT.md`

用于：

- 你对 Opencode 的固定循环口令
- 每一轮测试、验证、小修时反复使用

作用：

- 强制先 pull 最新代码
- 强制只做测试、验证、小修
- 强制更新 `docs/tasks/` 并 push

## 推荐使用方式

### 新开会话时

先发：

- `START_PROMPT.md`

### 进入持续推进后

对 Codex 反复发：

- `CODEX_LOOP_PROMPT.md`

对 Opencode 反复发：

- `OPENCODE_LOOP_PROMPT.md`

## 一句话原则

启动词负责“进入正确上下文”，循环词负责“稳定重复推进主线”。
