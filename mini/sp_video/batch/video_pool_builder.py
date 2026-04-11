"""
video_pool_builder.py - 单视频片段池构建

第三阶段最小版：为每个视频构建自己的候选片段池。
每个池包含若干片段，每个片段有基本信息。
"""


def build_video_segment_pool(video_id, intervals_list, base_scores=None):
    """
    为单个视频构建片段池。

    输入：
    - video_id: 视频 ID
    - intervals_list: 时间轴列表，格式如：
      [
        [{"start": 0, "end": 10, "text": "..."}, ...],
        [{"start": 5, "end": 15, "text": "..."}, ...],
      ]
    - base_scores: 基础评分列表（可选），与 intervals_list 一一对应

    返回：
    {
        "video_id": "...",
        "segments": [
            {
                "video_id": "...",
                "start": 0,
                "end": 10,
                "text": "...",
                "base_score": 7.5,
            },
            ...
        ]
    }
    """
    if base_scores is None:
        base_scores = [None] * len(intervals_list)

    segments = []
    for idx, intervals in enumerate(intervals_list):
        if not intervals:
            continue

        base_score = base_scores[idx] if idx < len(base_scores) else None

        for interval in intervals:
            segment = {
                "video_id": video_id,
                "start": interval.get("start", 0),
                "end": interval.get("end", 0),
                "text": interval.get("text", ""),
                "base_score": base_score,
                "interval_idx": idx,
            }
            segments.append(segment)

    return {
        "video_id": video_id,
        "segments": segments,
        "total_segments": len(segments),
    }


def build_multi_video_pools(video_sources, interval_candidates_map, score_map=None):
    """
    为多个视频构建各自的片段池。

    输入：
    - video_sources: 视频源列表 [{"video_id": "...", "video_path": "...", "srt_path": "..."}, ...]
    - interval_candidates_map: {video_id: [[interval1, interval2, ...], ...]}
    - score_map: {video_id: [score1, score2, ...]}（可选）

    返回：
    {
        "video_id": {
            "video_id": "...",
            "segments": [...],
            "total_segments": ...
        },
        ...
    }
    """
    pools = {}

    for source in video_sources:
        video_id = source["video_id"]
        intervals_list = interval_candidates_map.get(video_id, [])
        base_scores = score_map.get(video_id, []) if score_map else None

        pool = build_video_segment_pool(video_id, intervals_list, base_scores)
        pools[video_id] = pool

        print(f"[视频池] {video_id}: {pool['total_segments']} 个片段")

    return pools


if __name__ == "__main__":
    test_intervals = [
        [
            {"start": 0, "end": 10, "text": "第一段"},
            {"start": 10, "end": 20, "text": "第二段"},
        ],
        [
            {"start": 5, "end": 15, "text": "候选一"},
            {"start": 15, "end": 25, "text": "候选二"},
        ],
    ]
    test_scores = [7.5, 8.0]

    pool = build_video_segment_pool("A001", test_intervals, test_scores)
    print(f"\n视频池：{pool['video_id']}")
    print(f"片段数量：{pool['total_segments']}")
    for seg in pool["segments"][:3]:
        print(
            f"  - {seg['start']}-{seg['end']}: {seg['text']} (score={seg['base_score']})"
        )
