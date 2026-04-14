import settings


def _time_to_seconds(time_str):
    hh_mm_ss, milliseconds = time_str.replace(",", ".").split(".")
    hh, mm, ss = hh_mm_ss.split(":")
    return int(hh) * 3600 + int(mm) * 60 + float(f"{ss}.{milliseconds}")


def _score_duration_fit(total_duration):
    if total_duration < 20:
        return 2.0
    if total_duration < 30:
        return 6.0
    if total_duration < 45:
        return 7.5
    if total_duration < 60:
        return 9.0
    if total_duration < 90:
        return 8.8
    if total_duration < 120:
        return 8.3
    if total_duration <= 300:
        return 7.6
    return 6.0


def evaluate_quality(video_path, intervals):
    """单视频机器评分，返回适合后续人工回标的维度。"""
    valid_intervals = [item for item in intervals if item[0][0]]
    valid_count = len(valid_intervals)

    total_duration = 0.0
    for interval in valid_intervals:
        start, end = interval[0]
        total_duration += max(0, _time_to_seconds(end) - _time_to_seconds(start))

    if valid_count >= 5:
        video_score = 8.8
    elif valid_count >= 3:
        video_score = 7.6
    elif valid_count >= 2:
        video_score = 6.5
    else:
        video_score = 5.2

    transition_score = max(3.5, 9.0 - max(0, valid_count - 1) * 0.8)
    audio_score = 8.0
    duration_fit = _score_duration_fit(total_duration)

    if valid_count >= 4 and total_duration >= 35:
        completeness = 8.8
    elif valid_count >= 3 and total_duration >= 25:
        completeness = 7.6
    elif valid_count >= 2 and total_duration >= 18:
        completeness = 6.5
    else:
        completeness = 4.8

    total = (
        video_score * 0.22
        + transition_score * 0.20
        + audio_score * 0.14
        + duration_fit * 0.20
        + completeness * 0.24
    )

    return {
        "video": round(video_score, 2),
        "transition": round(transition_score, 2),
        "audio": round(audio_score, 2),
        "duration_fit": round(duration_fit, 2),
        "completeness": round(completeness, 2),
        "duration_sec": round(total_duration, 3),
        "segment_count": valid_count,
        "dimensions": {
            "clarity": round(video_score, 2),
            "rhythm": round(transition_score, 2),
            "audio_stability": round(audio_score, 2),
            "duration_fit": round(duration_fit, 2),
            "completeness": round(completeness, 2),
        },
        "target_distribution": getattr(settings, "BATCH_DURATION_BUCKETS", []),
        "total": round(total, 2),
    }
