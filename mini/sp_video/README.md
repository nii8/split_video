# sp_video 使用说明

`sp_video` 用来把一个长视频剪成更短的视频。

输入是同名的 `.mp4` 和 `.srt` 字幕文件，输出是剪辑后的视频。

例如：

```text
data/video/demo.mp4
data/video/demo.srt
```

这两个文件名字一样，程序就会认为它们是一组。

## 先看这三个入口

大多数时候只需要用下面三个脚本。

| 你想做什么 | 用哪个脚本 |
| --- | --- |
| 生成 1 到 2 分钟短视频 | `scripts/run_short.py` |
| 生成 4 到 6 分钟视频 | `scripts/run_5min.py` |
| 批量生成、评分、选出更好的结果 | `batch_generator.py` |

新人先从 `scripts/run_short.py` 看起，它最短，也最容易理解。

## 准备工作

进入目录：

```bash
cd sp_video
```

安装 Python 依赖：

```bash
pip install openai pyyaml
```

安装 FFmpeg。Linux 示例：

```bash
sudo apt install ffmpeg
```

配置 API Key：

```text
data/config/config.yaml
```

示例：

```yaml
DEEPSEEK_API_KEY: sk-xxxxxxxxxxxxxxxx
BAILIAN_API_KEY: sk-xxxxxxxxxxxxxxxx
```

## 最常用：生成短视频

把视频和字幕放到 `data/video`：

```text
data/video/
├── demo.mp4
└── demo.srt
```

运行：

```bash
python scripts/run_short.py --video_dir data/video --output_dir data/output_short
```

输出会在：

```text
data/output_short/
```

这个模式适合生成 60 到 150 秒左右的短视频。

## 生成 5 分钟视频

```bash
python scripts/run_5min.py --video_dir data/video --output_dir data/output_5min
```

这个模式适合把长视频压缩成 4 到 6 分钟左右的视频。

如果结果太短，`run_5min.py` 会再尝试一次扩写脚本。

## 只跑某一个视频

如果 `data/video` 里有很多视频，但你只想跑其中一个：

```bash
python scripts/run_short.py --video_dir data/video --output_dir data/output_short --video_id demo
```

`video_id` 就是文件名，不包含后缀。

例如文件是：

```text
demo.mp4
demo.srt
```

那么 `video_id` 就是：

```text
demo
```

5 分钟版本也是一样：

```bash
python scripts/run_5min.py --video_dir data/video --output_dir data/output_5min --video_id demo
```

## 多开几个终端一起跑

如果目录里有 10 个视频，可以开 5 个终端一起跑。

第一步，先初始化任务文件：

```bash
python scripts/run_short.py --init_tasks --video_dir data/video --output_dir data/output_short
```

第二步，在多个终端里运行同一条命令：

```bash
python scripts/run_short.py --auto --video_dir data/video --output_dir data/output_short
```

每个进程会自动领取一个还没跑的视频。一个视频失败后，这个进程会继续领取下一个视频。

5 分钟版本：

```bash
python scripts/run_5min.py --init_tasks --video_dir data/video --output_dir data/output_5min
python scripts/run_5min.py --auto --video_dir data/video --output_dir data/output_5min
```

任务文件默认放在：

```text
data/run_state/run_short_tasks.json
data/run_state/run_5min_tasks.json
```

默认不会覆盖已有任务文件。如果要重新生成任务文件，加 `--force`：

```bash
python scripts/run_short.py --init_tasks --force --video_dir data/video --output_dir data/output_short
```

## 为什么 ffmpeg 要排队

Phase1、Phase2、Phase3 可以多个进程同时跑。

但是 Phase4 要用 ffmpeg 生成视频。多个 ffmpeg 同时跑，机器容易卡，结果也不好排查。

所以代码里用了一个锁文件，让 ffmpeg 阶段排队执行：

```text
data/run_state/ffmpeg.lock
```

意思是：前面的 AI 分析可以并发，最后真正生成视频时一个一个来。

## 常用参数

`run_short.py` 和 `run_5min.py` 都支持这些参数：

| 参数 | 作用 |
| --- | --- |
| `--video_dir` | 输入目录，里面放同名 `.mp4` 和 `.srt` |
| `--output_dir` | 输出目录 |
| `--video_id` | 只处理一个指定视频 |
| `--force` | 输出已存在时也重新跑 |
| `--init_tasks` | 根据 `video_dir` 初始化任务文件 |
| `--auto` | 自动领取任务，一直跑到没有任务 |
| `--task_file` | 指定任务文件路径 |
| `--ffmpeg_lock_file` | 指定 ffmpeg 锁文件路径 |
| `--worker_id` | 可选，只是调试标记 |

查看完整参数：

```bash
python scripts/run_short.py --help
python scripts/run_5min.py --help
```

## 代码结构

先记住一句话：

```text
phase 是主流程，batch 是批量选优，shared 是公共工具。
```

目录：

```text
sp_video/
├── scripts/
│   ├── run_short.py          # 短视频入口
│   └── run_5min.py           # 5 分钟视频入口
├── phase1_select/            # 从字幕里选出候选内容
├── phase2_rewrite/           # 把候选内容改写成脚本
├── phase3_match/             # 把脚本匹配回原字幕时间
├── phase4_cut/               # 用 ffmpeg 按时间剪视频
├── batch/                    # 批量生成、评分、选优
├── shared/                   # 公共工具：LLM、日志、锁、任务队列
├── main.py                   # 简单 CLI 入口
├── batch_generator.py        # 批量入口
└── skill.py                  # 外部系统调用入口
```

## 主流程怎么走

```text
mp4 + srt
  ↓
Phase1：从字幕中选出重要内容
  ↓
Phase2：把内容改写成剪辑脚本
  ↓
Phase3：找到每句脚本对应原视频的时间
  ↓
Phase4：ffmpeg 按时间剪出新视频
```

每个阶段都会生成中间文件，方便排查问题：

```text
step1.txt        # Phase1 结果
step2.txt        # Phase2 结果
intervals.json   # Phase3 结果
output.mp4       # Phase4 结果
summary.json     # 本次运行摘要
events.jsonl     # 运行日志
```

## batch 目录是做什么的

`batch/` 是更复杂的批量系统。

它不是新人第一天必须看懂的部分。先会用 `run_short.py` 和 `run_5min.py` 就够了。

`batch/` 里面分四块：

```text
batch/
├── runner/          # 批量跑 Phase1、Phase2、Phase3
├── scoring/         # 给候选结果打分
├── multi_video/     # 多个视频片段组合
└── debug/           # 调试视觉评分
```

简单理解：

```text
runner 负责生成候选
scoring 负责判断好不好
multi_video 负责多个视频混剪
debug 负责看评分过程
```

## 不想调用 LLM，只做本地检查

这些命令不会真正跑业务，也不会调用 LLM：

```bash
python -m compileall shared phase1_select phase2_rewrite phase3_match phase4_cut batch scripts main.py skill.py batch_generator.py
python scripts/run_short.py --help
python scripts/run_5min.py --help
python skill.py --help
```

如果环境里安装了 `pytest`，可以跑部分测试：

```bash
python -m pytest tests/test_evaluator.py tests/test_filter_complex.py tests/test_time_utils.py tests/test_interval.py tests/test_mode2_parse.py
```

## 新人建议阅读顺序

按这个顺序看，不容易乱：

1. `scripts/run_short.py`
2. `phase1_select/runner.py`
3. `phase2_rewrite/runner.py`
4. `phase3_match/runner.py`
5. `phase4_cut/runner.py`
6. `shared/task_queue.py`
7. `shared/file_lock.py`
8. `batch/`

先理解单视频流程，再理解批量流程。

## 常见问题

### 1. 为什么没有输出视频？

先看输出目录里有没有这些文件：

```text
step1.txt
step2.txt
intervals.json
summary.json
events.jsonl
```

哪个文件没有生成，通常就是哪个阶段出问题。

### 2. 为什么 `--auto` 没有任务？

先确认是否已经初始化任务文件：

```bash
python scripts/run_short.py --init_tasks --video_dir data/video --output_dir data/output_short
```

再运行：

```bash
python scripts/run_short.py --auto --video_dir data/video --output_dir data/output_short
```

### 3. 为什么只想重建任务文件却没有覆盖？

默认不会覆盖已有任务文件。

需要加：

```bash
--force
```

### 4. 旧代码里 import 路径变了怎么办？

新的路径是：

```python
from batch.scoring.evaluator import evaluate_quality
from batch.runner.phase_runner import run_phase1_loop
from batch.multi_video.combiner import build_multi_video_candidates
```

不要再用旧路径：

```python
from batch.evaluator import evaluate_quality
from batch.phase_runner import run_phase1_loop
from batch.video_combiner import build_multi_video_candidates
```
