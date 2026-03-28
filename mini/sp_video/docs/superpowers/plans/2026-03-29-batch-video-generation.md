# 视频批量预生成系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现24小时运行的视频预生成系统，对已知视频库批量生成短视频候选，通过质量评分筛选最优结果

**Architecture:** 单进程顺序执行（方案C），无并发/线程/队列。Phase1→2→3→4→5 串行处理，失败即丢弃，结构化日志记录所有耗时操作。

**Tech Stack:** Python 3.8+, OpenCV, librosa, Qwen-VL (阿里云), FFmpeg

---

## 文件结构规划

**新增文件：**
- `batch_generator.py` - 主程序入口
- `batch/logger.py` - 结构化日志模块
- `batch/evaluator.py` - 质量评分模块
- `batch/phase_runner.py` - Phase1-5 批量执行封装

**修改文件：**
- `main.py` - 提取 `run_phase1_batch()` / `run_phase2_batch()` 函数
- `settings.py` - 添加批量生成相关配置

**新增测试：**
- `tests/test_evaluator.py` - 评分模块测试

**数据目录：**
- `data/batch_results/{video_id}/phase1-5/` - 各阶段输出
- `data/batch_log.jsonl` - 全局日志

---

## 实施步骤

### Step 1: 创建结构化日志模块

**文件:** `batch/logger.py` (新建)

**任务:**
- [x] 实现 `BatchLogger` 类
- [x] 方法: `log_phase(video_id, phase, iteration, duration_sec, status, **kwargs)`
- [x] 输出格式: JSONL (每行一个JSON)
- [x] 字段: ts, video_id, phase, iteration, duration_sec, status, reason(可选)
- [x] 同时输出到文件 (`data/batch_log.jsonl`) 和 stderr

**验收标准:**
```python
logger = BatchLogger("data/batch_log.jsonl")
logger.log_phase("C1873", "phase1", 1, 12.3, "success")
# 输出: {"ts": "2026-03-29T10:23:45", "video_id": "C1873", ...}
```

---

### Step 2: 重构 main.py 为批量模式

**文件:** `main.py` (修改)

**任务:**
- [x] 提取 `run_phase1_batch(video_id, srt_path, output_path)` 函数
  - 移除所有 `input()` 交互
  - 直接使用 `PHASE1_PROMPT`
  - 返回生成的文本内容
- [x] 提取 `run_phase2_batch(video_id, phase1_content, output_path)` 函数
  - 移除所有 `input()` 交互
  - 接受 phase1_content 作为输入
  - 返回生成的脚本内容
- [x] 保持原有 `run_phase1()` / `run_phase2()` 不变（向后兼容）

**验收标准:**
```python
content = run_phase1_batch("C1873", "data/hanbing/C1873/C1873.srt", "output.txt")
assert len(content) > 0
assert os.path.exists("output.txt")
```

---

### Step 3: 实现 Phase 执行封装

**文件:** `batch/phase_runner.py` (新建)

**任务:**
- [x] 实现 `run_phase1_loop(video_id, srt_path, output_dir, count=20)`
  - 循环调用 `run_phase1_batch()` count 次
  - 保存到 `output_dir/step1_{i:03d}.txt`
  - 记录每次耗时到日志
  - 返回成功的文件路径列表

- [x] 实现 `run_phase2_loop(video_id, phase1_files, output_dir, count=100)`
  - 从 phase1_files 随机选择作为输入
  - 循环调用 `run_phase2_batch()` count 次
  - 保存到 `output_dir/step2_{i:03d}.txt`
  - 返回成功的文件路径列表

- [x] 实现 `run_phase3_loop(video_id, srt_path, phase2_files, output_dir)`
  - 对每个 phase2 脚本调用 `get_keep_intervals()`
  - 失败即丢弃（不重试）
  - 保存成功的到 `output_dir/intervals_{i:03d}.json`
  - 返回 `[(idx, intervals), ...]`

**验收标准:**
```python
phase1_files = run_phase1_loop("C1873", "C1873.srt", "phase1/", count=20)
assert len(phase1_files) == 20
```

---

### Step 4: 实现质量评分模块

**文件:** `batch/evaluator.py` (新建)

**任务:**
- [x] 实现 `evaluate_quality(video_path, intervals)` 函数
- [x] 返回评分字典: `{"video": 4.0, "transition": 3.0, "audio": 3.0, "total": 10.0}`
- [x] 子函数:
  - `score_video_quality(video_path)` - 视频画面评分（4分）
  - `score_transitions(video_path, intervals)` - 拼接自然度（3分）
  - `score_audio_quality(video_path, intervals)` - 音频质量（3分）

**评分逻辑（简化版）:**
- 视频: 提取8帧 → Qwen-VL 检测人脸 → 基础分4分
- 拼接: 计算拼接点数量 → 每个拼接点 -0.5（最低0分）
- 音频: 提取音频 → librosa 计算平均音量 → 基础分3分

**验收标准:**
```python
score = evaluate_quality("C1873.mp4", intervals)
assert 0 <= score["total"] <= 10
assert "video" in score and "audio" in score
```

---

### Step 5: 实现主程序入口

**文件:** `batch_generator.py` (新建)

**任务:**
- [x] 实现 `scan_videos(data_dir)` - 扫描 data/hanbing/ 获取视频列表
- [x] 实现 `process_video(video_id)` - 处理单个视频的完整流程
  - Phase1: 20次字幕筛选
  - Phase2: 100次脚本生成
  - Phase3: 时间轴匹配（失败丢弃）
  - Phase4: 质量评分
  - Phase5: 生成视频（评分 >= 7）
- [x] 实现 `generate_summary(video_id)` - 生成该视频的统计报告
- [x] 实现 `main()` - 主循环，遍历所有视频

**验收标准:**
```bash
python batch_generator.py
# 输出日志到 stderr
# 生成 data/batch_results/{video_id}/summary.json
```

---

### Step 6: 添加配置和工具函数

**文件:** `settings.py` (修改)

**任务:**
- [x] 添加批量生成配置:
  - `BATCH_PHASE1_COUNT = 20`
  - `BATCH_PHASE2_COUNT = 100`
  - `BATCH_SCORE_THRESHOLD = 7.0`
  - `BATCH_RESULTS_DIR = "./data/batch_results"`
  - `BATCH_LOG_FILE = "./data/batch_log.jsonl"`

---

### Step 7: 编写测试

**文件:** `tests/test_evaluator.py` (新建)

**任务:**
- [x] 测试 `evaluate_quality()` 基本功能
- [x] 测试评分范围 0-10
- [x] 测试空 intervals 处理

---

### Step 8: 集成测试和文档

**任务:**
- [x] 在测试视频上运行完整流程
- [x] 验证日志格式正确
- [x] 验证 summary.json 生成
- [x] 更新 CLAUDE.md 添加批量生成说明

---

## 关键设计决策

1. **无并发**: 顺序执行，避免 LLM 速率限制（5小时1000次）
2. **失败即丢弃**: Phase3 匹配失败不重试，保持简单
3. **最小化评分**: 先实现基础评分逻辑，后续迭代优化
4. **复用现有代码**: 最大化复用 make_time/make_video 模块

---

## 风险和缓解

| 风险 | 缓解措施 |
|------|---------|
| LLM 速率限制 | 串行执行 + 日志记录请求次数 |
| Phase3 成功率低 | 记录失败原因，后续优化 prompt |
| 评分模块复杂 | 先实现简化版，分阶段迭代 |
| 磁盘空间不足 | 定期清理中间文件 |

---

## 验收标准

- [ ] 能处理 data/hanbing/ 下所有视频
- [ ] 每个视频生成 summary.json
- [ ] 日志文件格式正确（JSONL）
- [ ] 至少生成 1 个评分 >= 7 的视频
- [ ] 代码通过所有单元测试

