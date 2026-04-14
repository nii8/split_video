# 批量视频预生成系统

## 概述

24小时运行的视频预生成系统，对已知视频库批量生成短视频候选，通过质量评分筛选最优结果。

## 运行方式

```bash
python batch_generator.py
```

## 工作流程

1. **Phase1**: 对每个视频生成 20 次字幕筛选
2. **Phase2**: 从 Phase1 结果随机选择，生成 100 次脚本
3. **Phase3**: 时间轴匹配（失败即丢弃，不重试）
4. **Phase4**: 质量评分（0-10分）
5. **Phase5**: 生成视频（仅评分 >= 7 的）

## 输出结构

```
data/batch_results/{video_id}/
├── phase1/step1_001.txt ... step1_020.txt
├── phase2/step2_001.txt ... step2_100.txt
├── phase3/intervals_001.json ... (成功的)
├── phase4/score_001.json ... (评分结果)
├── phase5/video_001.mp4 ... (最终视频)
└── summary.json (统计汇总)
```

## 日志格式

日志输出到 `data/batch_log.jsonl`，每行一个 JSON：

```json
{"ts": "2026-03-29T10:23:45", "video_id": "C1873", "phase": "phase1", "iteration": 1, "duration_sec": 12.3, "status": "success"}
```

## 配置参数

在 `settings.py` 中修改：

- `BATCH_PHASE1_COUNT = 20` - Phase1 生成次数
- `BATCH_PHASE2_COUNT = 100` - Phase2 生成次数
- `BATCH_SCORE_THRESHOLD = 7.0` - 最低评分阈值

## 评分标准（简化版）

- **视频质量** (4分): 基于片段数量
- **拼接自然度** (3分): 片段越多扣分越多
- **音频质量** (3分): 基础分

总分 >= 7.0 才会生成最终视频。
