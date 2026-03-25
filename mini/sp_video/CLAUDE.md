# CLAUDE.md — sp_video 项目规范

## 工作模式: Superpowers + AI 协作

### 角色分工

**Claude (我) --- 架构师 / 项目经理**
- 需求分析 架构设计 任务拆分
- 使用Superpowers进行规划 审查 调试
- 代码审查 最终验收 git提交管理
- **不直接创建/修改 `.py` 文件**，所有编码任务必须委派给 Opencode
- 计划文档中的代码示例不算"写代码"

**Opencode --- 全能python开发**
- 项目代码开发 测试代码开发 其他开发任务
- 单元测试 集成测试
- 通过 `/ask opencode "..."` 调用

### 暂停机制

- Opencode 不可用 -- 暂停编码 等待恢复 (Claude 不会写代码)

### 协作方式

**使用Superpowers skills 进行**

- 规划 → `superpowers:writing-plans`
- 执行 → `superpowers:executing-plans`
- 审查 → `superpowers:requesting-code-review`
- 调试 → `superpowers:systematic-debugging`
- 完成 → `superpowers:finishing-a-development-branch`

**调用 AI 提供者执行代码任务**
```bash
# 指派Opencode 实现需求
/ask opencode "实现 XXX 需求功能, 涉及文件: ..."

# 查看执行结果
/pend opencode
```

## Linus 三问（决策前必问）

1. **这是现实问题还是想象问题？** → 拒绝过度设计
2. **有没有更简单的做法？** → 始终寻找最简方案
3. **会破坏什么？** → 向后兼容是铁律

## Git 规范

- 提交前必须通过代码审查
- 提交信息：`<类型>: <描述>`（中文）
- 类型：feat / fix / docs / refactor / chore
- 禁止：force push、修改已 push 历史

## 项目定位

CLI 工具：输入长视频 + SRT 字幕，通过 LLM 自动筛选和重组脚本，用 ffmpeg 剪出短视频。

---

## 运行命令

```bash
# 交互式主流程
python main.py

# OpenClaw 技能接口
python skill.py list
python skill.py start --video_id <id>
python skill.py phase2 --video_id <id>
python skill.py generate --video_id <id>

# 单元测试
pytest tests/ -v
```

---

## 目录结构

```
sp_video/
├── main.py              # 入口，4 个阶段串联，交互式 CLI
├── skill.py             # OpenClaw 技能接口：list / start / phase2 / generate
├── settings.py          # 全局配置（API Key、阈值、路径），其他模块统一 import settings
├── make_time/           # Phase 1-3：字幕解析 + AI 匹配 → 时间片段
│   ├── step2.py         # 对外接口：get_keep_intervals(srt_path, script)
│   ├── mode2.py         # 核心逻辑：解析脚本 → AI 匹配字幕 → 合并区间
│   ├── ai_caller.py     # AI 调用封装：匹配 + 相似度验证 + 降级搜索
│   ├── chat.py          # ask_ai()：底层 LLM 请求
│   ├── prompts.py       # 所有 prompt 构造函数
│   ├── interval.py      # 时间区间合并工具
│   └── time_utils.py    # 时间格式解析工具
├── make_video/
│   └── step3.py         # 对外接口：cut_video_main(keep_intervals, video_path, video_id, user_id)
│                        # 内部：ffmpeg 切片 → 合并视频 + 音频
├── tests/               # 单元测试（pytest）
│   ├── test_interval.py
│   ├── test_time_utils.py
│   └── test_mode2_parse.py
└── data/
    ├── config/
    │   └── config.yaml  # BAILIAN_API_KEY 等敏感配置（不入库）
    ├── hanbing/         # 视频数据：{video_id}/mp4 + srt
    ├── skill_state/     # 中间文件：{video_id}/state.json, step1.txt, step2.txt, intervals.json
    └── video_cache.json # OSS 视频摘要缓存
```

---

## 核心数据流

```
SRT 文件
  └─► parse_zimu_content()       → zimu_list: [[id, [start, end], text], ...]

LLM 脚本（Phase 2 输出）
  └─► get_yuanwen_mode2()        → yuanwen: [{part_name, zimu_list:[{start,end,text}]}, ...]

get_intervals_by_yuanwen()
  ├─► get_zimu_from_start_end()  → 精确时间匹配
  ├─► call_ai_match()            → AI 匹配 + 相似度验证（threshold=0.88）
  └─► find_intervals_by_ai()     → 降级：全文语义搜索

merge_intervals()               → keep_intervals: [[(start,end), text], ...]

cut_video_main()
  ├─► extract_audio()            → .wav（已有则跳过）
  ├─► cut_and_merge_audio()      → 临时片段 → concat → 输出 .wav
  └─► cut_and_merge_video_img()  → inpoint/outpoint concat → 输出 .mp4
      └─► ffmpeg merge           → 最终 output.mp4
```

---

## 关键约定

**对外接口（不要轻易改签名）**
- `get_keep_intervals(srt_path, script)` → `{'keep_intervals': [...], 'merged_intervals': [...]}`
- `cut_video_main(keep_intervals, video_path, video_id, user_id)` → `output_path: str`

**keep_intervals 格式**
```python
[
  [(start_time_str, end_time_str), text],   # 有效片段
  [(None, None), text],                     # 未匹配，phase4 会跳过
]
```
时间字符串格式：`"00:01:23,456"`（SRT 格式，逗号分隔毫秒）

**AI 匹配逻辑（两阶段）**
1. 主匹配：`call_ai_match()` → 返回 id_list，做相似度验证（> 0.88 通过，连续 ID 加 0.05）
2. 降级：`find_intervals_by_ai()` → 全文搜索，不做截断

**ffmpeg 临时文件**
- `wav/temp_audio_*.wav` — 音频片段（处理完自动清理）
- `concat_list.txt` — ffmpeg concat 列表（处理完自动清理）
- `temp_{video_id}.mp4` — 视频复制临时文件（处理完自动清理）
- `keep_intervals.json` — 每次运行后写入，用于调试

**配置加载**
直接从 `data/config/config.yaml` 加载配置

---

## LLM 使用

- Phase 1/2：Qwen，通过阿里云百炼 dashscope 调用，流式输出
- Phase 3 AI 匹配：Qwen，通过 `ask_ai()`，JSON 格式返回
- 模型名统一在 `mode2.py` 顶部 `glo_ask_modal_name = 'qwen'`

---

## 不要做的事

- 不要把 `main.py` 的 Phase 提示词移到外部文件（当前直接写在文件顶部，方便编辑）
- 不要在 `make_time/` 内部直接调用 ffmpeg（职责分离）
- 不要在 `make_video/` 内部调用 LLM（职责分离）
- `settings.py` 只做配置，不写业务逻辑
