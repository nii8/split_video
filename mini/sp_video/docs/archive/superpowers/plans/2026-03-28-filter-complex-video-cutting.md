# Filter Complex 视频剪辑重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将视频剪辑从关键帧对齐方案重构为 filter_complex 单次调用方案

**Architecture:** 使用 FFmpeg filter_complex 的 trim/atrim + concat 实现单次调用完成所有剪辑，替换现有的逐段切割+合并逻辑。音视频在同一时间轴处理，天然同步，无中间文件。

**Tech Stack:** FFmpeg filter_complex, Python subprocess

---

## 文件结构规划

**修改文件：**
- `make_video/step3.py` - 完全重构 `cut_video_main()` 和内部函数
- `settings.py` - 移除关键帧相关配置（可选，保持向后兼容）

**新增测试：**
- `tests/test_filter_complex.py` - filter_complex 字符串生成测试

**不变文件：**
- `main.py` - 接口不变
- `skill.py` - 接口不变
- `make_time/` - 完全不涉及

---

## 实施步骤

### Step 1: 创建 filter_complex 构建函数

**文件:** `make_video/filter_builder.py` (新建)

**任务:**
- [ ] 实现 `build_filter_complex(segments)` 函数
- [ ] 输入: `[(start_sec, end_sec), ...]` 时间片段列表（浮点数秒）
- [ ] 输出: filter_complex 字符串
- [ ] 逻辑: 遍历片段生成 trim/atrim + setpts/asetpts，最后拼接 concat

**验收标准:**
```python
segments = [(10.0, 20.0), (30.5, 40.3)]
result = build_filter_complex(segments)
# 应包含: [0:v]trim=start=10.0:end=20.0,setpts=PTS-STARTPTS[v0];
#         [0:a]atrim=start=10.0:end=20.0,asetpts=PTS-STARTPTS[a0];
#         ... concat=n=2:v=1:a=1[outv][outa]
```

---

### Step 2: 实现新的视频剪辑函数

**文件:** `make_video/step3.py`

**任务:**
- [ ] 新增 `cut_video_filter_complex(input_path, output_path, segments)` 函数
- [ ] 调用 `build_filter_complex()` 生成 filter 字符串
- [ ] 构建 ffmpeg 命令: `-filter_complex` + `-map [outv] -map [outa]`
- [ ] 编码参数: `-c:v libx264 -crf 23 -preset medium -c:a aac`
- [ ] 使用 subprocess 执行，捕获错误

**验收标准:**
- 单次 ffmpeg 调用完成剪辑
- 输出文件音画同步
- 无临时文件产生

---

### Step 3: 时间格式转换适配

**文件:** `make_video/step3.py`

**任务:**
- [ ] 实现 `srt_time_to_seconds(time_str)` 函数
- [ ] 输入: `"00:01:23,456"` (SRT 格式)
- [ ] 输出: `83.456` (浮点数秒)
- [ ] 在 `cut_video_main()` 中转换 `keep_intervals` 时间格式

**验收标准:**
```python
assert srt_time_to_seconds("00:01:23,456") == 83.456
assert srt_time_to_seconds("00:00:10,000") == 10.0
```

---

### Step 4: 重构 cut_video_main 主函数

**文件:** `make_video/step3.py`

**任务:**
- [ ] 保持函数签名不变: `cut_video_main(keep_intervals, video_path, video_id, user_id)`
- [ ] 移除旧逻辑: 关键帧提取、逐段切割、音频分离处理
- [ ] 新逻辑:
  1. 过滤 `keep_intervals` 中 `(None, None)` 的无效片段
  2. 转换时间格式为秒
  3. 调用 `cut_video_filter_complex()`
  4. 返回输出路径

**验收标准:**
- 接口兼容，`main.py` 和 `skill.py` 无需修改
- 代码行数减少 50% 以上
- 无临时文件残留

---

### Step 5: 单元测试

**文件:** `tests/test_filter_complex.py` (新建)

**任务:**
- [ ] 测试 `build_filter_complex()` 生成正确的 filter 字符串
- [ ] 测试单片段、多片段、边界情况
- [ ] 测试 `srt_time_to_seconds()` 时间转换

**验收标准:**
- `pytest tests/test_filter_complex.py -v` 全部通过

---

### Step 6: 集成测试

**文件:** 使用真实视频数据

**任务:**
- [ ] 选择测试视频 ID (如 `7Q3A0006`)
- [ ] 运行 `python skill.py generate --video_id <id>`
- [ ] 验证输出视频:
  - 音画同步
  - 时间轴准确
  - 无黑屏/卡顿
  - 文件大小合理

**验收标准:**
- 端到端流程成功
- 输出质量符合预期
- 性能可接受（对比旧方案）

---

### Step 7: 清理与文档

**任务:**
- [ ] 从 `step3.py` 移除旧代码: `extract_keyframes()`, `find_nearest_keyframe()` 等
- [ ] 从 `settings.py` 移除 `KEYFRAME_THRESHOLD` (可选)
- [ ] 更新 `CLAUDE.md` 核心数据流部分
- [ ] 归档 `key_frame_design.md` 到 `docs/archive/`

**验收标准:**
- 代码库无冗余代码
- 文档与实现一致

---

## 技术细节

### keep_intervals 格式处理

**输入格式:**
```python
[
  [("00:01:23,456", "00:02:30,789"), "文本"],
  [(None, None), "未匹配文本"],  # 跳过
  [("00:03:00,000", "00:04:15,500"), "文本2"]
]
```

**处理逻辑:**
```python
segments = []
for interval, text in keep_intervals:
    if interval[0] is None:
        continue
    start_sec = srt_time_to_seconds(interval[0])
    end_sec = srt_time_to_seconds(interval[1])
    segments.append((start_sec, end_sec))
```

### FFmpeg 命令结构

```bash
ffmpeg -i input.mp4 \
  -filter_complex "<生成的filter字符串>" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -crf 23 -preset medium \
  -c:a aac -b:a 192k \
  -y output.mp4
```

### 错误处理

- FFmpeg 执行失败 → 抛出异常，保留错误日志
- 空片段列表 → 提前返回错误
- 时间格式错误 → 抛出 ValueError

---

## 风险与降级

| 风险 | 影响 | 降级方案 |
|------|------|---------|
| filter_complex 语法错误 | 剪辑失败 | 详细日志 + 单元测试覆盖 |
| 大量片段导致命令过长 | 系统限制 | 分批处理（后续优化）|
| 编码速度慢 | 用户等待 | 调整 preset 参数 |

---

## 验收清单

- [ ] 所有单元测试通过
- [ ] 集成测试成功（至少 3 个不同视频）
- [ ] 音画同步验证通过
- [ ] 性能对比：处理时间 ≤ 旧方案 1.5 倍
- [ ] 代码审查通过（Codex review）
- [ ] 文档更新完成

---

## 预估工作量

- Step 1-3: 1-2 小时（核心逻辑）
- Step 4: 1 小时（重构主函数）
- Step 5-6: 1-2 小时（测试）
- Step 7: 0.5 小时（清理）

**总计:** 3.5-5.5 小时

---

## 参考资料

- FFmpeg filter_complex 文档: https://ffmpeg.org/ffmpeg-filters.html#concat
- 新方案设计文档: `video_cutting_design.md`
- 旧方案实现: `make_video/step3.py` (当前版本)
