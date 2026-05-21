"""
video_combiner.py - 多视频组合逻辑

第三阶段当前收口目标：
- 优先生成时长达标的双视频组合
- 主视频尽量承担更多时长，副视频做补充
- 保持组合顺序，不按不同源视频原始时间重新排序
"""


def get_candidate_total_duration(segments):
    return sum(max(0, seg.get("end", 0) - seg.get("start", 0)) for seg in segments)


def collect_following_segments(sorted_segments, first_seg, max_count, exclude_segments=None):
    parts = [first_seg]
    exclude_segments = exclude_segments or []

    for next_seg in sorted_segments:
        if len(parts) >= max_count:
            break
        if next_seg is first_seg or next_seg in exclude_segments or next_seg in parts:
            continue
        if next_seg["start"] >= parts[-1]["end"]:
            parts.append(next_seg)

    return parts


def extend_segments_until_duration(
    sorted_segments,
    parts,
    target_duration_sec,
    max_count,
    exclude_segments=None,
):
    exclude_segments = exclude_segments or []
    while len(parts) < max_count and get_candidate_total_duration(parts) < target_duration_sec:
        appended = False
        for next_seg in sorted_segments:
            if next_seg in exclude_segments or next_seg in parts:
                continue
            if next_seg["start"] >= parts[-1]["end"]:
                parts.append(next_seg)
                appended = True
                break
        if not appended:
            break
    return parts


def build_two_video_candidate(
    main_pool,
    sub_pool,
    max_candidates=20,
    min_duration_sec=18.0,
):
    """
    从两个视频池中生成组合候选。

    输入：
    - main_pool: 主视频池 {"video_id": "...", "segments": [...], ...}
    - sub_pool: 副视频池 {"video_id": "...", "segments": [...], ...}
    - max_candidates: 最大候选数量

    返回：
    [
        {
            "candidate_id": "C001",
            "segments": [
                {"video_id": "A", "start": 0, "end": 10, "text": "..."},
                {"video_id": "B", "start": 5, "end": 15, "text": "..."},
            ],
            "main_segments": [...],
            "sub_segments": [...],
        },
        ...
    ]
    """
    candidates = []
    candidate_id = 0

    main_segments = main_pool.get("segments", [])
    sub_segments = sub_pool.get("segments", [])

    if not main_segments or not sub_segments:
        return candidates

    main_segments_sorted = sorted(
        main_segments, key=lambda x: x.get("base_score") or 0, reverse=True
    )
    sub_segments_sorted = sorted(
        sub_segments, key=lambda x: x.get("base_score") or 0, reverse=True
    )

    candidates_with_duration = []

    main_limit = min(len(main_segments_sorted), max(12, max_candidates))
    sub_limit = min(len(sub_segments_sorted), max(8, max_candidates))

    for main_seg in main_segments_sorted[:main_limit]:
        for sub_seg in sub_segments_sorted[:sub_limit]:
            if candidate_id >= max_candidates:
                break

            candidate_id += 1

            # 主视频优先承担更多内容，先取连续 3 段。
            main_parts = collect_following_segments(
                main_segments_sorted,
                main_seg,
                max_count=4,
            )
            sub_parts = collect_following_segments(
                sub_segments_sorted,
                sub_seg,
                max_count=3,
            )

            # 如果组合仍偏短，继续向后补片段，优先补主视频，再补副视频。
            current_parts = main_parts + sub_parts
            if get_candidate_total_duration(current_parts) < min_duration_sec:
                main_parts = extend_segments_until_duration(
                    main_segments_sorted,
                    main_parts,
                    target_duration_sec=min_duration_sec - get_candidate_total_duration(sub_parts),
                    max_count=5,
                )
                current_parts = main_parts + sub_parts

            if get_candidate_total_duration(current_parts) < min_duration_sec:
                sub_parts = extend_segments_until_duration(
                    sub_segments_sorted,
                    sub_parts,
                    target_duration_sec=min_duration_sec - get_candidate_total_duration(main_parts),
                    max_count=4,
                )

            # 跨视频时不按各自源时间戳重排，保持组合顺序即可。
            all_segments = main_parts + sub_parts
            total_duration = get_candidate_total_duration(all_segments)

            candidate = {
                "candidate_id": f"C{candidate_id:03d}",
                "segments": all_segments,
                "main_segments": main_parts,
                "sub_segments": sub_parts,
                "main_video_id": main_pool["video_id"],
                "sub_video_id": sub_pool["video_id"],
                "total_duration": round(total_duration, 2),
            }

            candidates_with_duration.append((candidate, total_duration))

        if candidate_id >= max_candidates:
            break

    # 优先保留时长更接近交付目标、且片段数不过碎的候选。
    candidates_with_duration.sort(
        key=lambda item: (item[1] >= min_duration_sec, item[1], -len(item[0]["segments"])),
        reverse=True,
    )
    candidates = [item[0] for item in candidates_with_duration[:max_candidates]]

    print(f"[组合候选] 生成 {len(candidates)} 个候选")
    return candidates


def build_multi_video_candidates(pools, max_candidates=20, min_duration_sec=18.0):
    """
    从多个视频池中生成组合候选。

    第三阶段最小版：只处理主视频 + 第一个副视频。

    输入：
    - pools: {video_id: pool, ...}
    - max_candidates: 最大候选数量

    返回：
    [candidate1, candidate2, ...]
    """
    if len(pools) < 2:
        print("[警告] 视频池数量不足 2 个，无法生成多视频候选")
        return []

    pool_list = list(pools.values())
    main_pool = pool_list[0]
    sub_pool = pool_list[1]

    print(
        f"[多视频组合] 主视频：{main_pool['video_id']}, 副视频：{sub_pool['video_id']}"
    )

    return build_two_video_candidate(
        main_pool,
        sub_pool,
        max_candidates=max_candidates,
        min_duration_sec=min_duration_sec,
    )


if __name__ == "__main__":
    main_pool = {
        "video_id": "A001",
        "segments": [
            {
                "video_id": "A001",
                "start": 0,
                "end": 10,
                "text": "主 -1",
                "base_score": 8.0,
            },
            {
                "video_id": "A001",
                "start": 10,
                "end": 20,
                "text": "主 -2",
                "base_score": 7.5,
            },
            {
                "video_id": "A001",
                "start": 20,
                "end": 30,
                "text": "主 -3",
                "base_score": 7.0,
            },
        ],
    }

    sub_pool = {
        "video_id": "B002",
        "segments": [
            {
                "video_id": "B002",
                "start": 5,
                "end": 15,
                "text": "副 -1",
                "base_score": 7.8,
            },
            {
                "video_id": "B002",
                "start": 15,
                "end": 25,
                "text": "副 -2",
                "base_score": 7.2,
            },
        ],
    }

    candidates = build_two_video_candidate(main_pool, sub_pool, max_candidates=5)
    print(f"\n生成 {len(candidates)} 个候选")
    for c in candidates[:2]:
        print(f"  {c['candidate_id']}: {len(c['segments'])} 段")
        for seg in c["segments"]:
            print(
                f"    - [{seg['video_id']}] {seg['start']}-{seg['end']}: {seg['text']}"
            )
