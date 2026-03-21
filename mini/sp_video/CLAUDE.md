# CLAUDE.md — sp_video 项目规范

## 项目定位

CLI 工具：输入长视频 + SRT 字幕，通过 LLM 自动筛选和重组脚本，用 ffmpeg 剪出短视频。

---

## 目录结构

```
sp_video/
├── main.py              # 入口，4 个阶段串联，交互式 CLI
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
└── data/
    └── config/
        └── config.yaml  # DEEPSEEK_API_KEY 等敏感配置（不入库）
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

**配置加载优先级**
环境变量 > `data/config/config.yaml` > 默认值

---

## LLM 使用

- Phase 1/2：DeepSeek Chat，通过 OpenAI SDK 兼容接口调用，流式输出
- Phase 3 AI 匹配：DeepSeek，通过 `ask_ai()`，JSON 格式返回
- 模型名统一在 `mode2.py` 顶部 `glo_ask_modal_name = 'deepseek'`

---

## 不要做的事

- 不要把 `main.py` 的 Phase 提示词移到外部文件（当前直接写在文件顶部，方便编辑）
- 不要在 `make_time/` 内部直接调用 ffmpeg（职责分离）
- 不要在 `make_video/` 内部调用 LLM（职责分离）
- `settings.py` 只做配置，不写业务逻辑
