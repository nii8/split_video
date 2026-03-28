# 视频批量预生成系统设计文档

## 项目背景

为视频素材预生成大量候选短视频，通过多轮 LLM 生成 + 质量评分筛选出最优结果。

## 架构选择：方案 C（简单循环）

- LLM 限制：5小时1000次请求，串行执行更安全
- 视频规模：< 50 个视频，无需复杂并发
- 代码最简单（~300行），易于调试

## 核心流程

Phase1 (20次) → Phase2 (100次) → Phase3 (匹配) → Phase4 (评分) → Phase5 (生成)

## 技术实现

- batch/logger.py: JSONL 日志
- batch/phase_runner.py: 批量执行封装
- batch/evaluator.py: 质量评分（简化版）
- batch_generator.py: 主程序

## 运行方式

```bash
python batch_generator.py
```

输出到 `data/batch_results/{video_id}/` 和 `data/batch_log.jsonl`。
