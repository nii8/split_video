# sp_video — 智能视频自动剪辑 CLI

把一段长视频 + 字幕文件，自动剪成一条抖音爆款短视频。

---

## 安装

```bash
pip install openai pyyaml
# ffmpeg 需要系统级安装
sudo apt install ffmpeg   # Ubuntu
brew install ffmpeg       # macOS
```

---

## 配置

在 `data/config/config.yaml` 中填写 API Key：

```yaml
DEEPSEEK_API_KEY: sk-xxxxxxxxxxxxxxxx
```

也可以用环境变量覆盖：

```bash
export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

---

## 使用

```bash
python main.py
```

运行后按提示输入：

```
请输入视频路径 (.mp4): C1873.mp4
请输入字幕路径 (.srt): C1873.srt
```

每个阶段结束后，按回车确认继续。提示词默认即可，输入 `e` 可手动编辑。

输出文件示例：`C1873_cli_2026_03_21_09_01_22.mp4`

---

## 目录结构

```
sp_video/
├── main.py           # 入口，4 个阶段的主流程
├── settings.py       # 全局配置（API Key、路径等）
├── make_time/
│   └── step2.py      # get_keep_intervals：字幕匹配 → 时间片段
├── make_video/
│   └── step3.py      # cut_video_main：按片段切割视频
└── data/
    └── config/
        └── config.yaml   # API Key 配置文件
```

---

## 流程

```
输入: video.mp4 + video.srt
        │
        ▼
[Phase 1] LLM 从字幕中筛选高价值句子
        │
        ▼
[Phase 2] LLM 按爆款叙事逻辑重组脚本
        │
        ▼
[Phase 3] 字幕时间轴匹配 → 生成时间片段列表
        │
        ▼
[Phase 4] ffmpeg 按片段剪切 → 输出 output.mp4
```

每个阶段之间有手动确认，可以检查中间结果再继续。
