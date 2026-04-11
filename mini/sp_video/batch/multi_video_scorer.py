"""
multi_video_scorer.py - 多视频兼容评分

第三阶段最小版：只给最基础的兼容评分。
评分维度：
- 片段数量是否过多
- 是否跨视频切太多次
- 总长度是否太长
- 文本主题是否明显跑偏（简单关键词匹配）
"""


def score_multi_video_candidate(candidate, max_segments=5, max_duration_sec=60):
    """
    给多视频组合候选评分。

    输入：
    - candidate: {
        "segments": [...],
        "main_video_id": "...",
        "sub_video_id": "...",
      }
    - max_segments: 最大片段数
    - max_duration_sec: 最大总时长（秒）

    返回：
    {
        "multi_video_score": 8.5,
        "penalties": {
            "segment_count": 0,
            "video_switch": -0.5,
            "duration": 0,
            "text_coherence": 0,
        }
    }
    """
    score = 10.0
    penalties = {
        "segment_count": 0,
        "video_switch": 0,
        "duration": 0,
        "text_coherence": 0,
    }

    segments = candidate.get("segments", [])

    segment_count = len(segments)
    if segment_count > max_segments:
        penalty = min(2.0, (segment_count - max_segments) * 0.5)
        penalties["segment_count"] = -penalty
        score -= penalty

    video_switch_count = 0
    for i in range(1, len(segments)):
        if segments[i]["video_id"] != segments[i - 1]["video_id"]:
            video_switch_count += 1

    if video_switch_count >= 3:
        penalties["video_switch"] = -1.0
        score -= 1.0
    elif video_switch_count >= 2:
        penalties["video_switch"] = -0.5
        score -= 0.5

    total_duration = sum(seg["end"] - seg["start"] for seg in segments)
    if total_duration > max_duration_sec:
        penalty = min(2.0, (total_duration - max_duration_sec) / 30.0)
        penalties["duration"] = -penalty
        score -= penalty

    text_list = [seg.get("text", "") for seg in segments if seg.get("text")]
    if text_list:
        first_text = text_list[0].lower()
        coherence_penalty = 0
        for text in text_list[1:]:
            if not any(
                kw in text.lower()
                for kw in first_text.split()[:5]
                if len(first_text.split()) > 2
            ):
                coherence_penalty += 0.2
        coherence_penalty = min(1.5, coherence_penalty)
        if coherence_penalty > 0.5:
            penalties["text_coherence"] = -coherence_penalty
            score -= coherence_penalty

    score = max(0, min(10, score))

    return {
        "multi_video_score": round(score, 2),
        "penalties": {k: round(v, 2) for k, v in penalties.items()},
        "meta": {
            "segment_count": segment_count,
            "video_switch_count": video_switch_count,
            "total_duration": total_duration,
        },
    }


def merge_multi_video_score(score, multi_video_result):
    """
    将多视频评分合并回总分。

    输入：
    - score: 原有评分 {"total": 7.5, "base_total": 7.5, ...}
    - multi_video_result: {"multi_video_score": 8.5, ...}

    返回：
    {"total": 8.0, "base_total": 7.5, "multi_video": 8.5, ...}
    """
    base_total = score.get("base_total") or score.get("total", 0)
    multi_score = multi_video_result.get("multi_video_score", 10.0)

    weight_multi = 0.3
    weight_base = 0.7

    new_total = base_total * weight_base + multi_score * weight_multi
    new_total = max(0, min(10, new_total))

    merged = dict(score)
    merged["base_total"] = base_total
    merged["multi_video"] = multi_score
    merged["total"] = round(new_total, 2)

    return merged


if __name__ == "__main__":
    test_candidate = {
        "segments": [
            {"video_id": "A", "start": 0, "end": 10, "text": "这是第一段内容"},
            {"video_id": "A", "start": 10, "end": 20, "text": "这是第二段内容"},
            {"video_id": "B", "start": 5, "end": 15, "text": "这是副视频内容"},
        ],
        "main_video_id": "A",
        "sub_video_id": "B",
    }

    result = score_multi_video_candidate(test_candidate)
    print(f"多视频评分：{result['multi_video_score']}")
    print(f"扣分项：{result['penalties']}")

    old_score = {"total": 7.5, "base_total": 7.5}
    merged = merge_multi_video_score(old_score, result)
    print(f"\n合并后总分：{merged['total']}")
    print(f"  基础分：{merged['base_total']}")
    print(f"  多视频分：{merged['multi_video']}")
