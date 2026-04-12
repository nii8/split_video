# 多视频生成功能 - 测试计划

**版本**: 1.0  
**日期**: 2026-04-12  
**状态**: 已完成

---

## 一、测试目标

验证多视频生成功能的完整性和稳定性，确保：
1. 单视频模式正常工作
2. 多视频模式正常工作
3. 性能指标符合预期
4. 生成的视频文件有效

---

## 二、测试范围

### 2.1 功能模块

| 模块 | 测试类型 | 优先级 |
|------|---------|--------|
| `multi_video_builder.py` | 单元测试 + 集成测试 | P0 |
| `batch_generator.py` | 集成测试 + E2E 测试 | P0 |
| `video_combiner.py` | 集成测试 | P1 |
| `multi_video_scorer.py` | 集成测试 | P1 |
| `video_pool_builder.py` | 集成测试 | P1 |

### 2.2 运行模式

- **单视频模式**: `BATCH_MULTI_VIDEO_ENABLE = False`
- **多视频模式**: `BATCH_MULTI_VIDEO_ENABLE = True`
- **测试模式**: `BATCH_TEST_MODE = True`（快速验证）

---

## 三、测试策略

### 3.1 测试层次

```
┌─────────────────────────────────────┐
│         E2E 测试 (完整流程)          │
├─────────────────────────────────────┤
│      集成测试 (模块间交互)           │
├─────────────────────────────────────┤
│      单元测试 (单个函数/类)          │
└─────────────────────────────────────┘
```

### 3.2 测试数据

**必需**: 至少 2 个视频文件（.mp4 + .srt）

**推荐测试视频**:
- C1873 (主测试视频)
- IMG_17501 (多视频测试)
- IMG_17502 (多视频测试)

### 3.3 测试环境

| 环境 | 用途 |
|------|------|
| 本地开发环境 | 功能验证、调试 |
| 测试服务器 | 性能测试、稳定性测试 |

---

## 四、测试用例

### 4.1 单元测试

#### TestMultiVideoBuilder

| 用例 | 测试内容 | 预期结果 |
|------|---------|---------|
| `test_filter_complex_generation` | filter_complex 字符串生成 | 正确的 FFmpeg filter 语法 |
| `test_command_building` | FFmpeg 命令构建 | 包含所有必需参数 |
| `test_with_real_videos` | 真实视频生成 | 生成有效 MP4 文件 |
| `test_skip_invalid_segments` | 跳过无效片段 | 只处理有效片段 |
| `test_no_valid_segments_error` | 无有效片段错误 | 抛出 ValueError |

#### TestBatchGenerator

| 用例 | 测试内容 | 预期结果 |
|------|---------|---------|
| `test_scan_videos` | 视频扫描功能 | 找到所有视频 |
| `test_video_file_validity` | 视频文件验证 | ffprobe 验证通过 |
| `test_multi_video_requires_multiple_sources` | 多视频源要求 | 至少 2 个视频 |

### 4.2 集成测试

#### 场景 A: 单视频模式

**配置**:
```python
BATCH_MULTI_VIDEO_ENABLE = False
BATCH_TEST_MODE = True
BATCH_PHASE1_COUNT = 1
BATCH_PHASE2_COUNT = 1
```

**输入**: 1 个视频 (C1873)

**预期输出**:
- ✓ Phase1: 1 个字幕筛选结果
- ✓ Phase2: 1 个脚本生成结果
- ✓ Phase3: 有效时间片段
- ✓ Phase4: 基础评分
- ✓ Phase5: 至少 1 个视频文件

#### 场景 B: 多视频模式 (2 个视频)

**配置**:
```python
BATCH_MULTI_VIDEO_ENABLE = True
BATCH_TEST_MODE = True
```

**输入**: 2 个视频 (C1873, IMG_17501)

**预期输出**:
- ✓ 每个视频完成 phase1-phase3
- ✓ 生成多视频片段池
- ✓ 至少 5 个多视频候选
- ✓ 至少 1 个候选分数 >= 7.0
- ✓ 至少 1 个多视频文件

#### 场景 C: 多视频模式 (3 个视频)

**输入**: 3 个视频 (C1873, IMG_17501, IMG_17502)

**预期输出**:
- ✓ 更多候选组合
- ✓ 跨视频片段正确拼接
- ✓ 输出视频包含所有源视频片段

### 4.3 性能测试

#### 性能指标

| 阶段 | 预期时间 (测试模式) | 瓶颈阈值 |
|------|------------------|---------|
| Phase1 | < 60s | > 90s |
| Phase2 | < 120s | > 180s |
| Phase3 | < 40s | > 60s |
| Phase4 | < 10s | > 20s |
| Phase5 | < 30s | > 60s |
| **总计 (单视频)** | **< 10 分钟** | **> 15 分钟** |
| **总计 (多视频 3 源)** | **< 20 分钟** | **> 30 分钟** |

#### 资源指标

- CPU 使用率峰值：< 80%
- 内存使用峰值：< 2GB
- 磁盘空间：> 10GB 可用

---

## 五、测试执行

### 5.1 执行流程

```bash
# 1. 准备
cd mini/sp_video

# 2. 运行单元测试
pytest tests/test_multi_video_builder.py tests/test_batch_generator.py -v

# 3. 运行单视频集成测试
python3 scripts/run_comprehensive_test.py --mode single

# 4. 运行多视频集成测试
python3 scripts/run_comprehensive_test.py --mode multi

# 5. 性能分析
python3 scripts/analyze_performance.py

# 6. 生成测试报告
python3 scripts/generate_test_report.py --output final_test_report.md
```

### 5.2 一键执行

```bash
# 运行所有测试
python3 scripts/run_all_tests.py --output-report

# 查看报告
cat data/batch_results/test_reports/final_test_report.md
```

### 5.3 时间安排

| 阶段 | 预计时间 |
|------|---------|
| 单元测试 | 2 分钟 |
| 单视频集成测试 | 10 分钟 |
| 多视频集成测试 | 20 分钟 |
| 性能分析 | 5 分钟 |
| 报告生成 | 2 分钟 |
| **总计** | **~40 分钟** |

---

## 六、验收标准

### 6.1 功能验收

- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 单视频模式生成有效输出
- [ ] 多视频模式生成有效输出
- [ ] 生成的视频文件可播放（ffprobe 验证）

### 6.2 性能验收

- [ ] 单视频（测试模式）< 10 分钟
- [ ] 多视频 3 源（测试模式）< 20 分钟
- [ ] 无内存泄漏（内存增长 < 100MB）
- [ ] FFmpeg 进程正常退出

### 6.3 质量验收

- [ ] 代码覆盖率 > 80%
- [ ] 无严重错误（error/critical 日志）
- [ ] 错误处理健全（网络超时、文件缺失等）
- [ ] 日志完整可追溯

---

## 七、测试脚本

### 7.1 脚本清单

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `run_all_tests.py` | 一键运行所有测试 | 命令行参数 | 测试结果 |
| `run_comprehensive_test.py` | 运行单/多视频集成测试 | 模式、视频 ID | JSON/MD 报告 |
| `analyze_performance.py` | 性能数据分析 | 日志文件 | 性能报告 |
| `generate_test_report.py` | 生成最终测试报告 | 测试结果 | Markdown 报告 |

### 7.2 使用示例

```bash
# 完整测试
python3 scripts/run_all_tests.py --output-report

# 只测多视频模式
python3 scripts/run_comprehensive_test.py --mode multi

# 指定视频
python3 scripts/run_comprehensive_test.py --mode multi --videos C1873 IMG_17501

# 性能分析
python3 scripts/analyze_performance.py --output perf_report.md

# 生成报告
python3 scripts/generate_test_report.py --output final_report.md
```

---

## 八、风险和缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| AI API 超时 | Phase1/2 失败 | 中 | 重试机制、超时设置 |
| FFmpeg 编码失败 | Phase5 失败 | 低 | 验证输入参数、检查编解码器 |
| 磁盘空间不足 | 测试中断 | 低 | 测试前清理、监控空间 |
| 多视频音画不同步 | 质量问题 | 低 | PTS 调整验证 |
| 内存泄漏 | 系统不稳定 | 低 | 监控内存使用、及时清理 |

---

## 九、交付物

### 9.1 测试报告

**位置**: `data/batch_results/test_reports/final_test_report.md`

**内容**:
- 执行摘要
- 测试覆盖
- 功能验证
- 性能分析
- 错误和警告
- 结论

### 9.2 性能报告

**位置**: `data/batch_results/test_reports/performance_analysis.md`

**内容**:
- 各阶段耗时统计
- 瓶颈分析
- 优化建议

### 9.3 测试数据

**位置**: `data/batch_results/`

**内容**:
- JSON 格式测试结果
- 生成的视频文件
- 日志文件

---

## 十、后续改进

### 10.1 测试自动化

- [ ] 集成到 CI/CD 流程
- [ ] 定时回归测试
- [ ] 性能基线对比

### 10.2 测试覆盖

- [ ] 边界条件测试
- [ ] 异常场景测试
- [ ] 压力测试（大量视频）

### 10.3 性能优化

- [ ] Phase1/2 并行化
- [ ] FFmpeg 硬件加速
- [ ] 缓存机制

---

## 附录

### A. 相关文件

- [测试指南](TESTING_GUIDE.md)
- [多视频功能文档](reference/multi_video_phase3_guide.md)
- [批量生成指南](reference/batch_generation.md)

### B. 命令速查

```bash
# 快速验证
pytest tests/ -v

# 单视频测试
python3 scripts/run_comprehensive_test.py --mode single

# 多视频测试
python3 scripts/run_comprehensive_test.py --mode multi

# 完整测试
python3 scripts/run_all_tests.py --output-report
```

### C. 联系人

- 开发负责人：[姓名]
- 测试负责人：[姓名]
- 问题反馈：[GitHub Issues](https://github.com/nii8/split_video/issues)

---

*文档最后更新：2026-04-12*
