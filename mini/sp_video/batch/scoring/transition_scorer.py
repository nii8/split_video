"""
第二阶段：拼接自然度规则评分。

这里只做最简单版本，不做多模态切点评估。
先根据 intervals 本身判断：
1. 片段是不是太碎
2. 转场是不是太多
3. 时间跨度是不是太跳

这一步的目的，不是做精确导演判断，
而是先把明显“不自然”的候选压下去。
"""


def srt_time_to_seconds(time_str):
    h, m, s_ms = time_str.split(":")
    s, ms = s_ms.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def get_valid_segments(intervals):
    result = []
    for item in intervals:
        start_time, end_time = item[0]
        if not start_time or not end_time:
            continue
        start_sec = srt_time_to_seconds(start_time)
        end_sec = srt_time_to_seconds(end_time)
        if end_sec > start_sec:
            result.append([start_sec, end_sec])
    return result


def score_transition_naturalness(intervals):
    """
    只按规则做拼接自然度评分。
    返回 0-10 分，分数越高表示越自然。
    """
    segments = get_valid_segments(intervals)
    if not segments:
        return {
            "score": 0.0,
            "summary": "没有有效片段",
            "issues": ["no_segments"],
        }

    durations = []
    gaps = []
    for i, (start_sec, end_sec) in enumerate(segments):
        durations.append(end_sec - start_sec)
        if i > 0:
            prev_end = segments[i - 1][1]
            gaps.append(start_sec - prev_end)

    score = 10.0
    issues = []

    short_count = len([d for d in durations if d < 2.0])
    if short_count >= 3:
        score -= 2.0
        issues.append("too_many_short_segments")
    elif short_count >= 1:
        score -= 1.0
        issues.append("has_short_segments")

    segment_count = len(segments)
    if segment_count >= 12:
        score -= 2.0
        issues.append("too_many_cuts")
    elif segment_count >= 8:
        score -= 1.0
        issues.append("many_cuts")

    big_gap_count = len([g for g in gaps if g > 20])
    if big_gap_count >= 3:
        score -= 2.0
        issues.append("too_many_big_jumps")
    elif big_gap_count >= 1:
        score -= 1.0
        issues.append("has_big_jumps")

    avg_duration = sum(durations) / len(durations)
    if avg_duration < 2.5:
        score -= 1.0
        issues.append("avg_duration_too_short")

    score = max(0.0, round(score, 2))
    summary = "拼接较自然"
    if issues:
        summary = "存在片段过碎或时间跳跃问题"

    return {
        "score": score,
        "summary": summary,
        "issues": issues,
    }


def merge_transition_score(score, transition_result, transition_weight=0.2):
    """
    把拼接自然度分并回总分。
    total 保持为最终分。
    """
    merged = dict(score)
    old_total = merged.get("total", 0)
    merged["transition_natural"] = transition_result["score"]
    merged["transition_summary"] = transition_result["summary"]
    merged["transition_issues"] = transition_result["issues"]
    merged["total_before_transition"] = round(old_total, 2)
    merged["total"] = round(old_total * (1 - transition_weight) + transition_result["score"] * transition_weight, 2)
    return merged


def enrich_candidates_with_transition_score(scored_candidates):
    """
    给所有候选补一层规则版拼接自然度评分。
    这一步很便宜，所以直接全量做。
    """
    result = []
    for idx, intervals, score in scored_candidates:
        transition_result = score_transition_naturalness(intervals)
        new_score = merge_transition_score(score, transition_result)
        result.append((idx, intervals, new_score))
    return result
