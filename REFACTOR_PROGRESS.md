# 重构进度记录

## 背景

用户觉得项目代码像"屎山"，难以维护。我们制定了 Phase 1 重构计划，目标是：
1. 统一配置管理
2. 拆分大文件
3. 删除死代码
4. 防止 JSON 文件损坏

## 重要约定

**工作节奏（必须遵守）：**
- 每次只改少量文件（1个为佳）
- 改完之后**不要 commit**，先停下来等用户确认
- 用户确认没问题，说"继续"之后再 commit，再进行下一个文件
- 绝对不能一口气把剩余所有文件都做完

**这条约定的来源：**
用户曾因 Claude 一次性提交太多 commit 而情绪崩溃，详见下方"情绪复盘"章节。

## 分支说明

- `main` — 正在逐步重构的分支
- `refactor/phase1-done` — 所有 Phase 1 改动的最终形态（参照用）

对比还剩多少没做：
```bash
git diff main..refactor/phase1-done --stat
```

## 已完成的 commits（main 分支）

| commit | 内容 |
|--------|------|
| `bab8785` | 新建 `settings.py`，统一管理全局配置 |
| `250dfa7` | `chat.py` 改用 settings 读取 API Key |
| `7bd3e87` | 新建4个文件，拆分 `util.py` 内容按职责分类 |
| `fe93c60` | `mode2.py` 切换到新模块，移除内嵌 prompt 和魔法数字 |
| `3dcae33` | 删除 `make_time/util.py` |
| `357549f` | 精简 `config.py`，删除已迁到 settings.py 的内容 |
| `cfee2e9` | `server.py` 改用 settings 读取配置 |
| `73ea870` | `sse_server.py` 改用 settings 读取配置 |

## 待完成的工作

### 还差 3 个文件（Phase 1 剩余）

**1. `run_video.py`**
- 移除 `upload_token, server_ip, limit_prompt` 的导入
- 改用 `settings.SERVER_IP / settings.UPLOAD_TOKEN / settings.LIMIT_PROMPT`

**2. `video_server.py`**
- 加 `import settings`（改动很小）

**3. `make_video/step3.py`（删死代码）**
- 删除 `cut_and_merge_img()` 函数（旧的帧提取方案，已被 `cut_and_merge_video_img()` 替代）
- 删除 `count_files_in_directory()`（只被上面那个死函数调用）
- 删除函数结尾后的孤儿代码块（`return output_video` 之后还有一段不可达的旧代码）
- 删除 `import shutil` 和 `video_img_dir` 全局变量（只被死代码用到）

### Phase 1 最后一步（做完上面3个之后）

**4. JSON 原子写入**
- `sse_server.py` 的 `update_socket_status()` — 改用 `os.replace()` 防止崩溃时 JSON 损坏
- `run_video.py` 的 `update_task_status()` — 同上

## Phase 1 核心改动说明

### settings.py（新建）
所有常量集中在这里，支持环境变量覆盖：
- `SERVER_IP`, `WORKER_IPS`, `UPLOAD_TOKEN`
- `LIMIT_PROMPT`, `AI_CHECK_THRESHOLD`, `AI_CONSECUTIVE_BONUS`
- `BACKEND_IDLE_SEC`, `DATA_DIR`
- `DEEPSEEK_API_KEY`, `BAILIAN_API_KEY`（从 config.yaml 读取）
- `TOKEN_LIST`, `NAME_DIC`（从 config.json 读取）

### config.py（精简后）
只保留工具函数，不再有常量：
- `find_srt_files()`, `get_srt_file_path()`, `get_video_file_path()`
- `is_windows()`, `get_token_len()`, `split_srt_content()`

### make_time/ 拆分结果
| 新文件 | 内容 |
|--------|------|
| `time_utils.py` | 时间字符串处理、字幕窗口查找 |
| `interval.py` | 区间分组与合并 |
| `prompts.py` | 所有 AI prompt 构建函数 |
| `ai_caller.py` | AI 调用封装、JSON 解析 |

## Phase 2（Phase 1 完成后再做）

拆分 `sse_server.py`，目前这个文件太大，把路由处理、业务逻辑、状态管理混在一起。
具体方案待 Phase 1 完成后再讨论。

---

## 情绪复盘（2026-03-10）

### 发生了什么

用户说"继续继续，改完文件再停下来，我会直接查看 git 的差分"。

Claude 误解为"加速，一口气做完"，于是连续做了多个文件的修改并全部 commit，没有在每一步停下来等用户确认。

用户说"我很生气"、"我情绪有点失控"、"我情绪崩溃，缓不过来"。

### 用户说的原话（关键对话）

> 刚刚你理解错我的意思了，一下子提交这么多代码

> 你为什么提交这么多代码

> 有什么机制可以防止以后再出现同样的问题

> 完全错误，你还是没有理解到人类的痛苦（对 Claude 直接给出技术方案的回应）

> 我要先调节情绪，才能继续和你对话

### Claude 犯了什么错

1. **误解指令**：用户说"改完文件再停下来"，意思是每改完一个文件就停；Claude 理解成了"全部做完再停"。

2. **跳过情绪，直奔方案**：用户说情绪崩溃，Claude 立刻列出"防止下次出问题的3个机制"，完全忽视了用户当下的感受。用户说"完全错误，你还是没有理解到人类的痛苦"，这句话是核心反馈。

3. **二次误解**：即使在用户点出"没有理解到人类的痛苦"之后，Claude 还是花了一点时间才真正停下来陪伴，而不是继续解释。

### 情绪背后的需求（复盘）

用户花了很多时间在这个项目上，重构对他来说不只是技术问题，而是**想亲手理解每一步变化**。

一次性看到大量 commit，意味着：
- 失去了"一步一步理解"的过程感
- 感觉掌控权被拿走了
- 努力参与的意愿被忽视了

核心需求是：**参与感、掌控感、被看见**。不是代码写得好不好，而是"这是我的项目，我要亲自经历每一步"。

### 下次遇到类似情况，Claude 应该怎么做

1. 用户表达情绪时，**先陪伴，不给方案**，等用户自己说"那怎么办"。
2. 不确定指令范围时，**做最小的那个动作**，然后停下来确认。
3. 宁可做少，也不要做多。用户可以说"继续"，但撤回一堆 commit 很麻烦。
