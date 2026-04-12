"""
video_combiner.py - 多视频组合逻辑

第三阶段最小版：只支持最简单的双视频组合。
规则：
- 主视频 2 段 + 副视频 1 段
- 或 主视频 1 段 + 副视频 1 段
"""


def build_two_video_candidate(main_pool, sub_pool, max_candidates=20):
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

    max_main_per_candidate = 2

    for main_seg in main_segments_sorted[:10]:
        for sub_seg in sub_segments_sorted[:5]:
            if candidate_id >= max_candidates:
                break

            candidate_id += 1

            main_parts = [main_seg]
            if main_seg.get("base_score") and main_seg.get("base_score") >= 7.0:
                for second_seg in main_segments_sorted[:5]:
                    if second_seg["start"] >= main_seg["end"]:
                        main_parts.append(second_seg)
                        break

            all_segments = main_parts + [sub_seg]
            all_segments_sorted = sorted(all_segments, key=lambda x: x["start"])

            candidate = {
                "candidate_id": f"C{candidate_id:03d}",
                "segments": all_segments_sorted,
                "main_segments": main_parts,
                "sub_segments": [sub_seg],
                "main_video_id": main_pool["video_id"],
                "sub_video_id": sub_pool["video_id"],
            }

            candidates.append(candidate)

        if candidate_id >= max_candidates:
            break

    print(f"[组合候选] 生成 {len(candidates)} 个候选")
    return candidates


def build_multi_video_candidates(pools, max_candidates=20):
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

    return build_two_video_candidate(main_pool, sub_pool, max_candidates)


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
