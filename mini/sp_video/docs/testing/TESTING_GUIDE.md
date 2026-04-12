# 多视频生成功能 - 测试指南

## 目录

- [快速开始](#快速开始)
- [测试脚本说明](#测试脚本说明)
- [运行测试](#运行测试)
- [测试报告](#测试报告)
- [故障排查](#故障排查)

---

## 快速开始

### 一键运行所有测试

```bash
cd mini/sp_video

# 运行完整测试套件
python3 scripts/run_all_tests.py --output-report

# 查看生成的报告
cat data/batch_results/test_reports/final_test_report.md
```

### 快速验证（测试模式）

```bash
# 单视频模式快速测试
python3 scripts/run_comprehensive_test.py --mode single

# 多视频模式快速测试
python3 scripts/run_comprehensive_test.py --mode multi
```

---

## 测试脚本说明

### 1. `scripts/run_all_tests.py`
**功能**: 一键运行所有测试  
**用途**: CI/CD、完整验证

```bash
# 运行所有测试
python3 scripts/run_all_tests.py --output-report

# 跳过某些测试
python3 scripts/run_all_tests.py --skip-unit --skip-single

# 指定视频
python3 scripts/run_all_tests.py --videos C1873 IMG_17501
```

### 2. `scripts/run_comprehensive_test.py`
**功能**: 运行单视频或多视频模式集成测试  
**用途**: 功能验证、性能测试

```bash
# 单视频模式
python3 scripts/run_comprehensive_test.py --mode single

# 多视频模式
python3 scripts/run_comprehensive_test.py --mode multi

# 指定视频
python3 scripts/run_comprehensive_test.py --mode multi --videos C1873 IMG_17501 IMG_17502

# 指定输出目录
python3 scripts/run_comprehensive_test.py --mode single --output-dir /tmp/test_output
```

### 3. `scripts/analyze_performance.py`
**功能**: 分析性能数据，识别瓶颈  
**用途**: 性能优化

```bash
# 分析日志
python3 scripts/analyze_performance.py --log data/batch_log.jsonl

# 输出到文件
python3 scripts/analyze_performance.py --output performance_report.md
```

### 4. `scripts/generate_test_report.py`
**功能**: 生成 Markdown 测试报告  
**用途**: 验收报告

```bash
# 生成报告
python3 scripts/generate_test_report.py --output final_report.md
```

### 5. `tests/test_batch_generator.py`
**功能**: pytest 集成测试  
**用途**: 自动化测试

```bash
# 运行所有测试
pytest tests/test_batch_generator.py -v

# 运行特定测试类
pytest tests/test_batch_generator.py::TestMultiVideoMode -v

# 运行特定测试函数
pytest tests/test_batch_generator.py::TestMultiVideoBuilder::test_generate_multi_video -v
```

### 6. `tests/test_multi_video_builder.py`
**功能**: multi_video_builder 单元测试  
**用途**: 核心逻辑验证

```bash
pytest tests/test_multi_video_builder.py -v
```

---

## 运行测试

### 前置条件

1. **测试视频文件**

确保 `data/hanbing/` 目录下有至少 2 个视频文件：
```bash
ls data/hanbing/
# 应该看到：C1873, IMG_17501, IMG_17502 等
```

2. **依赖安装**

```bash
pip install pytest pyyaml
```

3. **FFmpeg**

```bash
ffmpeg -version
ffprobe -version
```

### 测试模式配置

测试脚本会自动设置以下配置：

| 配置项 | 测试模式值 | 说明 |
|--------|-----------|------|
| `BATCH_TEST_MODE` | `True` | 启用测试模式 |
| `BATCH_PHASE1_COUNT` | `1` | Phase1 迭代次数 |
| `BATCH_PHASE2_COUNT` | `1` | Phase2 迭代次数 |
| `BATCH_MULTI_VIDEO_ENABLE` | `True/False` | 根据模式设置 |

### 测试流程

```
1. 扫描视频文件
   ↓
2. Phase1: 字幕筛选 (AI)
   ↓
3. Phase2: 脚本生成 (AI)
   ↓
4. Phase3: 时间轴匹配 (AI)
   ↓
5. Phase4: 质量评分
   ↓
6. Phase5: 视频生成 (FFmpeg)
   ↓
7. 验证输出
   ↓
8. 生成报告
```

---

## 测试报告

### 报告位置

测试报告生成在：
```
data/batch_results/test_reports/
├── test_report_single_YYYYMMDD_HHMMSS.json
├── test_report_single_YYYYMMDD_HHMMSS.md
├── test_report_multi_YYYYMMDD_HHMMSS.json
├── test_report_multi_YYYYMMDD_HHMMSS.md
├── performance_analysis.md
└── final_test_report.md
```

### 报告内容

**JSON 报告** 包含：
- 测试日期、模式、视频 ID
- 各阶段耗时
- 生成的视频列表
- 错误和警告

**Markdown 报告** 包含：
- 执行摘要
- 测试覆盖
- 功能验证
- 性能分析
- 错误和警告
- 结论

### 示例报告片段

```markdown
## 执行摘要

| 项目 | 值 |
|------|-----|
| 测试状态 | ✓ PASSED |
| 测试模式 | multi |
| 总耗时 | 185.42 秒 |
| 生成视频 | 3 个 |
| 视频有效率 | 3/3 (100.0%) |

## 性能分析

### 阶段耗时统计

| 阶段 | 平均 (s) | 最小 (s) | 最大 (s) | 次数 |
|------|----------|----------|----------|------|
| phase1 | 45.23 | 42.10 | 48.36 | 3 |
| phase2 | 89.67 | 85.20 | 94.14 | 3 |
| phase3 | 32.45 | 30.12 | 34.78 | 3 |
| phase5 | 18.07 | 15.30 | 20.84 | 3 |
```

---

## 故障排查

### 常见问题

#### 1. 找不到视频文件

**错误**: `未找到视频文件`

**解决**:
```bash
# 检查视频目录
ls data/hanbing/

# 确保有 .mp4 和 .srt 文件
ls data/hanbing/C1873/
```

#### 2. FFmpeg 错误

**错误**: `ffmpeg: command not found`

**解决**:
```bash
# 安装 FFmpeg
sudo apt-get install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg      # CentOS/RHEL
```

#### 3. AI API 调用失败

**错误**: `Phase1/Phase2 failed: API error`

**解决**:
- 检查 `data/config/config.yaml` 中的 API Key
- 检查网络连接
- 查看 `data/batch_log.jsonl` 详细错误

#### 4. 测试超时

**现象**: 测试运行时间过长

**解决**:
```bash
# 使用测试模式
# 已自动设置 BATCH_TEST_MODE=True

# 或手动减少迭代次数
# 编辑 settings.py:
# BATCH_PHASE1_COUNT = 1
# BATCH_PHASE2_COUNT = 1
```

### 日志位置

- **批量日志**: `data/batch_log.jsonl`
- **测试报告**: `data/batch_results/test_reports/`
- **生成视频**: `data/batch_results/{video_id}/phase5/`
- **多视频输出**: `data/batch_results/multi_video/generated_videos/`

### 调试技巧

1. **查看详细日志**
```bash
cat data/batch_log.jsonl | python3 -m json.tool | less
```

2. **验证视频文件**
```bash
ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=codec_type,codec_name \
  -of json data/batch_results/multi_video/generated_videos/*.mp4
```

3. **清理测试数据**
```bash
# 清理测试报告
rm -rf data/batch_results/test_reports/

# 清理生成视频（保留 summary）
rm -rf data/batch_results/*/phase5/
rm -rf data/batch_results/multi_video/generated_videos/
```

---

## 验收标准

### 功能验收
- [x] 单元测试全部通过
- [x] 单视频模式生成有效视频
- [x] 多视频模式生成有效视频
- [x] 生成的视频可播放（H.264 + AAC）

### 性能验收
- [x] 单视频（测试模式）< 10 分钟
- [x] 多视频 3 源（测试模式）< 20 分钟
- [x] 视频生成成功率 > 90%

### 质量验收
- [x] 无严重错误
- [x] 错误处理健全
- [x] 日志完整

---

## 更多信息

- [多视频功能文档](../docs/reference/multi_video_phase3_guide.md)
- [批量生成指南](../docs/reference/batch_generation.md)
- [性能优化建议](../docs/core/total.md)
