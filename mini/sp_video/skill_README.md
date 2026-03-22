# sp_video 技能说明文档

## 技能功能

将 OSS 上的长视频（MP4 + SRT 字幕）通过 AI 自动剪辑为抖音风格短视频，并上传回 OSS 返回公网链接。

整个流程分四个阶段，需与用户多轮确认：

1. **Phase1** — LLM 筛选字幕中有价值的句子（自动执行，无需确认）
2. **Phase2** — LLM 重组为短视频脚本（需用户确认提示词）
3. **Phase3** — AI 将脚本句子匹配到字幕时间轴（完成后需用户确认时间序列）
4. **Phase4** — ffmpeg 剪辑视频 → 上传 OSS → 返回链接

---

## 调用方式

技能通过子进程调用，所有输出为 **UTF-8 JSON**，进度日志输出到 stderr。

```bash
python skill.py <命令> [参数]
```

---

## 命令详细说明

### 1. `list` — 查询可用视频列表

**用途**：用户问"有哪些视频"时调用。

```bash
python skill.py list
```

**执行逻辑**：
1. 执行 `ossutil ls oss://kaixin-v/hanbing/2026`
2. 解析出成对的 `.mp4` + `.srt` 文件，提取 `video_id`
3. 对比本地缓存 `data/video_cache.json`：
   - OSS 已删除的视频 → 从缓存移除
   - 新视频 → 下载 SRT → LLM 生成摘要 → 写入缓存
4. 返回完整列表

**返回示例**：
```json
{
  "status": "success",
  "total": 3,
  "new": 1,
  "removed": 0,
  "videos": [
    {
      "id": "7Q3A0006",
      "summary": "一位企业家讲述创业失败经历，探讨韧性与重新出发的主题。",
      "month": "03",
      "batch": "001"
    },
    {
      "id": "7Q3A0012",
      "summary": "职场导师分享如何在高压环境下保持专注力的实用方法。",
      "month": "03",
      "batch": "001"
    }
  ]
}
```

**展示给用户的方式**：
> 共找到 3 个视频：
> - **7Q3A0006** — 一位企业家讲述创业失败经历，探讨韧性与重新出发的主题。
> - **7Q3A0012** — 职场导师分享如何在高压环境下保持专注力的实用方法。
>
> 请问您想处理哪个视频编号？

---

### 2. `start` — 开始处理视频（Phase1）

**用途**：用户选择视频编号后调用。

```bash
python skill.py start --video_id 7Q3A0006
```

**执行逻辑**：
1. 从缓存获取 OSS 路径
2. 下载 MP4 + SRT 到本地 `data/hanbing/7Q3A0006/`（已有则跳过）
3. 自动执行 Phase1（LLM 筛选字幕），无需用户干预
4. 返回 Phase2 默认提示词供用户确认

**返回示例**：
```json
{
  "status": "need_confirm_prompt",
  "video_id": "7Q3A0006",
  "message": "Phase1 完成。以下是 Phase2 的默认提示词，可直接确认或修改。",
  "default_prompt": "核心指令：请你担任一位短视频脚本架构师...",
  "phase1_preview": "00:00:19,833 --> 00:00:20,633\n知己知彼\n\n00:00:27,400 --> 00:00:30,300\n不是99%..."
}
```

**展示给用户的方式**：
> Phase1 完成，已筛选出有价值的字幕片段。
>
> 以下是 Phase2 的脚本重组提示词（默认），您可以：
> 1. 直接**确认**使用默认提示词
> 2. **修改**提示词后告诉我新的内容
>
> 默认提示词：
> ```
> 核心指令：请你担任一位短视频脚本架构师...
> ```

---

### 3. `phase2` — 生成脚本并匹配时间轴（Phase2 + Phase3）

**用途**：用户确认（或修改）提示词后调用。

```bash
# 有缓存时第一次调用 → 返回 need_confirm_regen，询问用户
python skill.py phase2 --video_id 7Q3A0006

# 用户确认使用缓存
python skill.py phase2 --video_id 7Q3A0006 --use_cache

# 用户要求重新生成
python skill.py phase2 --video_id 7Q3A0006 --force

# 使用用户修改的提示词（从文件读取，避免 shell 转义问题）
python skill.py phase2 --video_id 7Q3A0006 --prompt_file /tmp/custom_prompt.txt
```

**执行逻辑**：
1. 若已有上次缓存的脚本（step2.txt），且未指定 `--use_cache` / `--force`，返回 `need_confirm_regen`
2. `--use_cache`：跳过 Phase2，直接用缓存脚本执行 Phase3
3. `--force` 或 `--prompt_file`：重新执行 Phase2 再执行 Phase3
4. 返回匹配到的时间片段列表供用户确认

**缓存确认返回示例**（有旧脚本时）：
```json
{
  "status": "need_confirm_regen",
  "video_id": "7Q3A0006",
  "message": "已有上次生成的脚本缓存，是否直接使用？",
  "cached_script_preview": "00:00:19,833 --> 00:00:20,633\n知己知彼\n...",
  "hint": "使用缓存: phase2 --video_id ... --use_cache  |  重新生成: phase2 --video_id ... --force"
}
```

**展示给用户的方式**（need_confirm_regen）：
> 上次已生成过脚本，预览如下：
> ```
> 00:00:19,833 --> 00:00:20,633
> 知己知彼
> ...
> ```
> 是否直接使用上次脚本？还是重新生成？

用户回答后：
- 用上次的 → `phase2 --video_id 7Q3A0006 --use_cache`
- 重新生成 → `phase2 --video_id 7Q3A0006 --force`
- 用自定义提示词 → 将新提示词写入文件，`phase2 --video_id 7Q3A0006 --prompt_file /tmp/p.txt`

**匹配完成返回示例**：
```json
{
  "status": "need_confirm_intervals",
  "video_id": "7Q3A0006",
  "message": "已匹配 8 个片段，请确认后生成视频。",
  "count": 8,
  "intervals": [
    {"start": "00:00:27,400", "end": "00:00:30,300", "text": "不是99% 是99.99%"},
    {"start": "00:01:15,000", "end": "00:01:22,500", "text": "失败不是终点，而是转折"},
    {"start": "00:02:33,100", "end": "00:02:40,800", "text": "你唯一的选择就是站起来"}
  ]
}
```

**展示给用户的方式**：
> Phase2+3 完成！已匹配 **8 个片段**：
>
> 1. `00:00:27` → `00:00:30` — 不是99% 是99.99%
> 2. `00:01:15` → `00:01:22` — 失败不是终点，而是转折
> 3. `00:02:33` → `00:02:40` — 你唯一的选择就是站起来
> ...（共8条）
>
> 是否确认以上片段，开始生成视频？

---

### 4. `generate` — 生成视频并上传（Phase4）

**用途**：用户确认时间序列后调用。

```bash
python skill.py generate --video_id 7Q3A0006
```

**执行逻辑**：
1. 执行 Phase4（ffmpeg 剪辑合并视频）
2. 上传到 `oss://kaixin1109/hanbing/2026/{month}/{batch}/{video_id}/{filename}`
3. 返回公网访问链接

**返回示例**：
```json
{
  "status": "success",
  "video_id": "7Q3A0006",
  "filename": "7Q3A0006_cli_2026_03_21_20_21_27.mp4",
  "oss_path": "oss://kaixin1109/hanbing/2026/03/001/7Q3A0006/7Q3A0006_cli_2026_03_21_20_21_27.mp4",
  "url": "http://video.kaixin.wiki/hanbing/2026/03/001/7Q3A0006/7Q3A0006_cli_2026_03_21_20_21_27.mp4",
  "message": "视频生成并上传成功！"
}
```

**展示给用户的方式**：
> 视频已生成并上传！
>
> 点击观看：http://video.kaixin.wiki/hanbing/2026/03/001/7Q3A0006/7Q3A0006_cli_2026_03_21_20_21_27.mp4

---

## 错误返回格式

所有错误统一格式：

```json
{
  "status": "error",
  "stage": 2,
  "message": "Phase 2 失败: API 调用超时"
}
```

`stage` 字段标识哪个阶段出错（`list`/`start` 命令无此字段）。

---

## 完整多轮对话流程

```
用户: 有哪些视频？
你 → skill.py list → 展示视频列表 → 询问选择

用户: 处理 7Q3A0006
你 → skill.py start --video_id 7Q3A0006 → 展示默认提示词 → 询问确认

用户: 确认（或：把提示词改成...）
你 → 如需修改，先将新提示词写入 /tmp/prompt_7Q3A0006.txt
   → skill.py phase2 --video_id 7Q3A0006 [--force | --use_cache | --prompt_file /tmp/prompt_7Q3A0006.txt]
   → 若返回 need_confirm_regen（有缓存），询问用户是否复用上次脚本
   → 展示时间片段列表 → 询问确认

用户: 确认
你 → skill.py generate --video_id 7Q3A0006 → 展示视频链接
```

---

## 本地文件结构（运行后自动生成）

```
sp_video/
└── data/
    ├── video_cache.json          # 视频列表 + 摘要缓存（跨会话持久化）
    ├── hanbing/
    │   └── {video_id}/           # 从 OSS 下载的原始文件
    │       ├── {video_id}.mp4
    │       └── {video_id}.srt
    └── skill_state/
        └── {video_id}/           # 每个视频的中间处理文件
            ├── state.json        # 当前处理阶段和路径信息
            ├── step1.txt         # Phase1 LLM 输出（缓存，重复调用可跳过）
            ├── step2.txt         # Phase2 LLM 输出（缓存）
            └── intervals.json    # Phase3 时间序列（缓存）
```

**中间文件缓存机制**：如果 `step1.txt` / `step2.txt` / `intervals.json` 已存在，重复调用时会自动跳过对应阶段。若需重新生成，删除对应文件即可。

---

## 依赖要求

- Python 3.8+
- `ossutil` 已安装并配置 OSS 访问凭证
- `ffmpeg` 已安装
- `data/config/config.yaml` 中配置 `DEEPSEEK_API_KEY`
