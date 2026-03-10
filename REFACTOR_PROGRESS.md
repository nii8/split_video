# 重构进度记录

## 背景

用户觉得项目代码像"屎山"，难以维护。我们制定了 Phase 1 重构计划，目标是：
1. 统一配置管理
2. 拆分大文件
3. 删除死代码
4. 防止 JSON 文件损坏

## 重要约定

**工作节奏（必须遵守）：**
- 每次只改一个文件
- 改完立即 commit，然后**停下来等用户确认**
- 用户说"继续"才进行下一个文件

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
