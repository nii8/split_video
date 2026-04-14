# 多视频组合生成（第三阶段）

## 概述

第三阶段实现了多视频组合生成功能，允许从多个视频源中提取片段并合成一个最终视频。该功能是 V2 三阶段路线图的最后一部分。

当前状态：

- 主功能已经接入
- 真实环境已报告生成过多视频成片
- 但默认配置和工程化验收仍在继续加固

## 功能特点

- **多视频源支持**：从多个视频中提取片段
- **智能组合**：根据评分和内容连贯性选择最佳片段组合
- **自动评分**：包括片段数量、视频切换频率、持续时间和文本连贯性评分
- **批量处理**：支持批量生成多个候选组合
- **视频生成**：将高分候选生成为实际的视频文件

## 配置选项

在 `settings.py` 中配置：

```python
BATCH_MULTI_VIDEO_ENABLE = False   # 默认关闭，验收或生产启用时再手动打开
BATCH_TEST_MODE = True            # 测试模式（降低AI调用次数）
BATCH_SCORE_THRESHOLD = 7.0       # 生成视频的最低分数阈值
```

## 工作流程

1. **视频扫描**：扫描 `data/hanbing/` 目录下的所有视频
2. **单视频处理**：为每个视频独立运行 Phase1-Phase3
3. **片段池构建**：为每个视频构建候选片段池
4. **组合生成**：从多个视频池中生成组合候选
5. **评分**：对每个组合进行综合评分
6. **视频生成**：将高分候选生成为实际视频文件
7. **结果输出**：生成 `summary.json` 和视频文件

## 输出结构

```
data/batch_results/multi_video/
├── summary.json              # 汇总信息
├── generated_videos/         # 生成的视频文件
│   ├── multi_video_C001.mp4
│   ├── multi_video_C002.mp4
│   └── ...
```

## 使用方法

### 启用多视频模式

```bash
python batch_generator.py
```

当 `BATCH_MULTI_VIDEO_ENABLE = True` 且目录中有多个视频时，系统会进入多视频模式。

### 测试模式

在 `settings.py` 中设置：

```python
BATCH_TEST_MODE = True  # 降低Phase1/2调用次数，加快测试
```

## 验收说明

- 运行产物默认写到 `data/batch_results/multi_video/`
- `generated_videos/` 与 `summary.json` 属于运行结果，不应提交到 git
- 示例脚本只能作为手动验证入口，不能替代正式验收

## 模块说明

- `batch/video_combiner.py` - 多视频组合逻辑
- `batch/multi_video_selector.py` - 多视频源选择
- `batch/video_pool_builder.py` - 视频片段池构建
- `batch/multi_video_scorer.py` - 多视频评分
- `make_video/multi_video_builder.py` - 多视频生成器

## 评分维度

1. **片段数量**：避免片段过多
2. **视频切换**：惩罚频繁的视频源切换
3. **持续时间**：避免过长或过短的视频
4. **文本连贯性**：确保内容的连贯性
