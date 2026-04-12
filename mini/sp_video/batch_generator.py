import os
import sys
import json
import time
import math
import settings
from batch.logger import BatchLogger
from batch.phase_runner import run_phase1_loop, run_phase2_loop, run_phase3_loop
from batch.evaluator import evaluate_quality
from batch.visual_scorer import enrich_top_interval_candidates_with_visual_score
from batch.transition_scorer import enrich_candidates_with_transition_score
from batch.video_pool_builder import keep_intervals_to_segments
from batch.video_combiner import build_multi_video_candidates
from batch.multi_video_scorer import (
    score_multi_video_candidate,
    merge_multi_video_score,
)
from make_video.step3 import cut_video_main
from make_video.multi_video_builder import generate_multi_video


def get_interval_total_duration(keep_intervals):
    total = 0.0
    for interval in keep_intervals:
        if not interval or not interval[0][0]:
            continue
        start, end = interval[0]
        total += max(0, cut_video_time_to_seconds(end) - cut_video_time_to_seconds(start))
    return round(total, 3)


def cut_video_time_to_seconds(time_str):
    time_str = time_str.replace(",", ".")
    hh_mm_ss, milliseconds = time_str.split(".")
    hh, mm, ss = hh_mm_ss.split(":")
    return int(hh) * 3600 + int(mm) * 60 + float(f"{ss}.{milliseconds}")


def get_duration_bucket(duration_sec, bucket_config):
    for bucket in bucket_config:
        min_sec = bucket.get("min_sec", 0)
        max_sec = bucket.get("max_sec")
        if duration_sec >= min_sec and (max_sec is None or duration_sec < max_sec):
            return bucket["label"]
    if bucket_config:
        return bucket_config[-1]["label"]
    return "unknown"


def compute_bucket_targets(total_count, bucket_config):
    if total_count <= 0 or not bucket_config:
        return {}

    total_probability = sum(bucket.get("probability", 0) for bucket in bucket_config) or 1.0
    raw_targets = []
    assigned = 0
    for bucket in bucket_config:
        ratio = bucket.get("probability", 0) / total_probability
        raw = total_count * ratio
        floor_value = int(math.floor(raw))
        raw_targets.append((bucket["label"], floor_value, raw - floor_value))
        assigned += floor_value

    remainder = max(0, total_count - assigned)
    raw_targets.sort(key=lambda item: item[2], reverse=True)

    targets = {label: floor_value for label, floor_value, _ in raw_targets}
    for label, _, _ in raw_targets[:remainder]:
        targets[label] += 1

    return targets


def select_candidates_by_bucket(
    candidates,
    target_count,
    bucket_config,
    score_threshold=None,
):
    if not candidates or target_count <= 0:
        return []

    bucket_targets = compute_bucket_targets(target_count, bucket_config)
    preferred = [c for c in candidates if score_threshold is None or c["score_total"] >= score_threshold]
    remaining = list(candidates)
    selected = []
    used_ids = set()

    for bucket in bucket_config:
        label = bucket["label"]
        need = bucket_targets.get(label, 0)
        if need <= 0:
            continue

        bucket_candidates = [
            c for c in preferred if c["duration_bucket"] == label and c["candidate_key"] not in used_ids
        ]
        bucket_candidates.sort(key=lambda x: x["score_total"], reverse=True)

        for candidate in bucket_candidates[:need]:
            selected.append(candidate)
            used_ids.add(candidate["candidate_key"])

    if len(selected) < target_count:
        for candidate in remaining:
            if candidate["candidate_key"] in used_ids:
                continue
            selected.append(candidate)
            used_ids.add(candidate["candidate_key"])
            if len(selected) >= target_count:
                break

    selected.sort(key=lambda x: (x["score_total"], x["duration_sec"]), reverse=True)
    return selected[:target_count]


def scan_videos(data_dir):
    """扫描视频目录，返回 [(video_id, srt_path, mp4_path), ...]"""
    videos = []
    for video_id in os.listdir(data_dir):
        video_dir = os.path.join(data_dir, video_id)
        if not os.path.isdir(video_dir):
            continue
        srt_path = os.path.join(video_dir, f"{video_id}.srt")
        mp4_path = os.path.join(video_dir, f"{video_id}.mp4")
        if os.path.exists(srt_path) and os.path.exists(mp4_path):
            videos.append((video_id, srt_path, mp4_path))
    return videos


def scan_multi_video_sources(data_dir):
    """
    扫描多视频源，返回视频源列表。
    格式：[{"video_id": "...", "video_path": "...", "srt_path": "..."}, ...]
    """
    sources = []
    for video_id in os.listdir(data_dir):
        video_dir = os.path.join(data_dir, video_id)
        if not os.path.isdir(video_dir):
            continue
        srt_path = os.path.join(video_dir, f"{video_id}.srt")
        mp4_path = os.path.join(video_dir, f"{video_id}.mp4")
        if os.path.exists(srt_path) and os.path.exists(mp4_path):
            sources.append(
                {
                    "video_id": video_id,
                    "video_path": mp4_path,
                    "srt_path": srt_path,
                }
            )
    return sources


def process_video(video_id, srt_path, mp4_path, logger):
    """处理单个视频的完整流程"""
    total_start = time.time()
    phase_stats = {}
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"开始处理视频 {video_id}", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)

    base_dir = os.path.join(settings.BATCH_RESULTS_DIR, video_id)

    # Phase1: 多次字幕筛选
    phase1_dir = os.path.join(base_dir, "phase1")
    start = time.time()
    phase1_files = run_phase1_loop(
        video_id, srt_path, phase1_dir, settings.BATCH_PHASE1_COUNT, logger
    )
    phase_stats["phase1_sec"] = round(time.time() - start, 2)
    if not phase1_files:
        print(f"[错误] Phase1 全部失败，跳过视频 {video_id}", file=sys.stderr)
        logger.log_event(
            "video_summary",
            video_id=video_id,
            total_duration_sec=round(time.time() - total_start, 2),
            **phase_stats,
        )
        return

    # Phase2: 多次脚本生成
    phase2_dir = os.path.join(base_dir, "phase2")
    start = time.time()
    phase2_files = run_phase2_loop(
        video_id, phase1_files, phase2_dir, settings.BATCH_PHASE2_COUNT, logger
    )
    phase_stats["phase2_sec"] = round(time.time() - start, 2)
    if not phase2_files:
        print(f"[错误] Phase2 全部失败，跳过视频 {video_id}", file=sys.stderr)
        logger.log_event(
            "video_summary",
            video_id=video_id,
            total_duration_sec=round(time.time() - total_start, 2),
            **phase_stats,
        )
        return

    # Phase3: 时间轴匹配
    phase3_dir = os.path.join(base_dir, "phase3")
    start = time.time()
    phase3_results = run_phase3_loop(
        video_id, srt_path, phase2_files, phase3_dir, logger
    )
    phase_stats["phase3_sec"] = round(time.time() - start, 2)
    if not phase3_results:
        print("[警告] Phase3 全部失败，没有有效时间序列", file=sys.stderr)
        logger.log_event(
            "video_summary",
            video_id=video_id,
            total_duration_sec=round(time.time() - total_start, 2),
            **phase_stats,
        )
        return

    # Phase4: 先按原来的规则做一轮基础评分
    phase4_dir = os.path.join(base_dir, "phase4")
    os.makedirs(phase4_dir, exist_ok=True)
    start = time.time()
    scored = []
    for idx, intervals in phase3_results:
        score_start = time.time()
        score = evaluate_quality(mp4_path, intervals)
        duration = time.time() - score_start
        score_path = os.path.join(phase4_dir, f"score_{idx:03d}.json")
        with open(score_path, "w", encoding="utf-8") as f:
            json.dump(score, f, ensure_ascii=False, indent=2)
        logger.log_phase(
            video_id, "phase4", idx, duration, "success", total_score=score["total"]
        )
        scored.append((idx, intervals, score))
    phase_stats["phase4_sec"] = round(time.time() - start, 2)

    # 第一阶段新增：
    # 这里只给前几个候选补一层视觉评分，不改原来的主流程。
    if getattr(settings, "BATCH_VISUAL_ENABLE", False) and scored:
        visual_dir = os.path.join(base_dir, "visual")
        os.makedirs(visual_dir, exist_ok=True)
        start = time.time()
        scored = enrich_top_interval_candidates_with_visual_score(
            video_id,
            mp4_path,
            scored,
            visual_dir,
            logger=logger,
            top_n=getattr(settings, "BATCH_VISUAL_TOPN", 2),
            use_llm=getattr(settings, "BATCH_VISUAL_USE_LLM", False),
        )
        phase_stats["visual_sec"] = round(time.time() - start, 2)

    # 第二阶段最小版：
    # 先不用多模态切点评分，只按 intervals 规则判断“是不是太碎、太跳”。
    if getattr(settings, "BATCH_TRANSITION_ENABLE", False) and scored:
        start = time.time()
        scored = enrich_candidates_with_transition_score(scored)
        phase_stats["transition_sec"] = round(time.time() - start, 2)

    candidate_infos = []
    for idx, intervals, score in scored:
        candidate_infos.append(
            {
                "candidate_key": f"{video_id}_{idx:03d}",
                "idx": idx,
                "intervals": intervals,
                "score": score,
                "score_total": score.get("total", 0),
                "duration_sec": get_interval_total_duration(intervals),
                "duration_bucket": get_duration_bucket(
                    get_interval_total_duration(intervals),
                    settings.BATCH_DURATION_BUCKETS,
                ),
            }
        )

    candidate_infos.sort(
        key=lambda item: (item["score_total"], item["duration_sec"]), reverse=True
    )
    selected_candidates = select_candidates_by_bucket(
        candidate_infos,
        target_count=getattr(settings, "BATCH_SINGLE_VIDEO_TARGET_PER_SOURCE", 10),
        bucket_config=getattr(settings, "BATCH_DURATION_BUCKETS", []),
        score_threshold=getattr(settings, "BATCH_SCORE_THRESHOLD", None),
    )

    # Phase5: 按时长分布配置生成单视频候选，优先满足每源视频目标数量。
    phase5_dir = os.path.join(base_dir, "phase5")
    os.makedirs(phase5_dir, exist_ok=True)
    start = time.time()
    generated = []
    for candidate in selected_candidates:
        idx = candidate["idx"]
        intervals = candidate["intervals"]
        score = candidate["score"]
        start = time.time()
        try:
            output_path = cut_video_main(intervals, mp4_path, video_id, "batch")
            final_path = os.path.join(phase5_dir, f"video_{idx:03d}.mp4")
            os.rename(output_path, final_path)
            duration = time.time() - start
            logger.log_phase(
                video_id, "phase5", idx, duration, "success", output=final_path
            )
            generated.append(
                {
                    "candidate_key": candidate["candidate_key"],
                    "path": final_path,
                    "idx": idx,
                    "duration_sec": round(candidate["duration_sec"], 3),
                    "duration_bucket": candidate["duration_bucket"],
                    "machine_score": score,
                }
            )
        except Exception as e:
            duration = time.time() - start
            logger.log_phase(
                video_id, "phase5", idx, duration, "failed", reason=str(e)
            )
    phase_stats["phase5_sec"] = round(time.time() - start, 2)

    generate_summary(
        video_id,
        base_dir,
        phase1_files,
        phase2_files,
        phase3_results,
        candidate_infos,
        selected_candidates,
        generated,
    )
    print(
        f"[完成] 视频 {video_id} 处理完成，生成 {len(generated)} 个视频",
        file=sys.stderr,
    )
    total_duration_sec = round(time.time() - total_start, 2)
    logger.log_event(
        "video_summary",
        video_id=video_id,
        total_duration_sec=total_duration_sec,
        generated_count=len(generated),
        phase1_count=len(phase1_files),
        phase2_count=len(phase2_files),
        phase3_success=len(phase3_results),
        **phase_stats,
    )
    print(f"[VIDEO TOTAL] {video_id}: {total_duration_sec} s", file=sys.stderr)


def run_single_video_phases(video_id, srt_path, mp4_path, logger):
    base_dir = os.path.join(settings.BATCH_RESULTS_DIR, video_id)

    phase1_dir = os.path.join(base_dir, "phase1")
    phase1_files = run_phase1_loop(
        video_id, srt_path, phase1_dir, settings.BATCH_PHASE1_COUNT, logger
    )
    if not phase1_files:
        return None

    phase2_dir = os.path.join(base_dir, "phase2")
    phase2_files = run_phase2_loop(
        video_id, phase1_files, phase2_dir, settings.BATCH_PHASE2_COUNT, logger
    )
    if not phase2_files:
        return None

    phase3_dir = os.path.join(base_dir, "phase3")
    phase3_results = run_phase3_loop(
        video_id, srt_path, phase2_files, phase3_dir, logger
    )
    if not phase3_results:
        return None

    all_segments = []
    for idx, keep_intervals in phase3_results:
        segments = keep_intervals_to_segments(video_id, keep_intervals)
        if not segments:
            continue

        score = evaluate_quality(mp4_path, keep_intervals)
        base_score = score.get("total", 0)
        for seg in segments:
            seg["base_score"] = base_score
            seg["interval_idx"] = idx
            all_segments.append(seg)

    if not all_segments:
        return None

    return {
        "video_id": video_id,
        "segments": all_segments,
    }


def process_multi_video(videos_data, logger):
    """
    处理多视频组合流程（第三阶段最小版）。

    输入：
    - videos_data: [(video_id, srt_path, mp4_path), ...]
    - logger: BatchLogger 实例

    流程：
    1. 构建视频源列表
    2. 为每个视频跑 phase1-phase3，得到候选片段
    3. 构建多视频片段池
    4. 生成多视频组合候选
    5. 评分并写出 summary
    """
    total_start = time.time()
    phase_stats = {}
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"开始多视频组合流程，共 {len(videos_data)} 个视频", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)

    old_phase1_count = settings.BATCH_PHASE1_COUNT
    old_phase2_count = settings.BATCH_PHASE2_COUNT
    if getattr(settings, "BATCH_TEST_MODE", False):
        settings.BATCH_PHASE1_COUNT = getattr(settings, "BATCH_TEST_PHASE1_COUNT", 3)
        settings.BATCH_PHASE2_COUNT = getattr(settings, "BATCH_TEST_PHASE2_COUNT", 20)
        print(
            f"[多视频模式] 临时降低参数：Phase1={settings.BATCH_PHASE1_COUNT}, Phase2={settings.BATCH_PHASE2_COUNT}",
            file=sys.stderr,
        )

    try:
        per_video_results = []
        source_videos = []

        start = time.time()
        for video_id, srt_path, mp4_path in videos_data:
            print(f"\n[多视频] 处理视频 {video_id} 的候选片段...", file=sys.stderr)
            result = run_single_video_phases(video_id, srt_path, mp4_path, logger)
            if result is None:
                print(f"  - 警告：{video_id} 没有有效候选", file=sys.stderr)
                continue

            per_video_results.append(result)
            source_videos.append(video_id)
            print(
                f"  - 生成 {len(result['segments'])} 个有效片段",
                file=sys.stderr,
            )
        phase_stats["per_video_phase1234_sec"] = round(time.time() - start, 2)

        if not per_video_results:
            print("[错误] 所有视频都没有有效片段，跳过", file=sys.stderr)
            return

        if len(per_video_results) < 2:
            print("[错误] 有效视频不足 2 个，跳过多视频生成", file=sys.stderr)
            return

        start = time.time()
        pools = {}
        for result in per_video_results:
            video_id = result["video_id"]
            pools[video_id] = {
                "video_id": video_id,
                "segments": result["segments"],
                "total_segments": len(result["segments"]),
            }
            print(
                f"[多视频池] {video_id}: {len(result['segments'])} 个片段",
                file=sys.stderr,
            )
        phase_stats["pool_build_sec"] = round(time.time() - start, 2)

        start = time.time()
        candidates = build_multi_video_candidates(
            pools,
            max_candidates=getattr(settings, "BATCH_MULTI_VIDEO_CANDIDATE_COUNT", 150),
            min_duration_sec=settings.BATCH_MIN_MULTI_VIDEO_DURATION_SEC,
        )
        print(f"[多视频] 生成 {len(candidates)} 个组合候选", file=sys.stderr)
        phase_stats["candidate_build_sec"] = round(time.time() - start, 2)

        if not candidates:
            print("[错误] 没有生成有效候选，跳过", file=sys.stderr)
            return

        start = time.time()
        scored_candidates = []
        for candidate in candidates:
            mv_result = score_multi_video_candidate(
                candidate,
                min_duration_sec=settings.BATCH_MIN_MULTI_VIDEO_DURATION_SEC,
            )
            base_score = 7.5
            for seg in candidate.get("segments", []):
                if seg.get("base_score") is not None:
                    base_score = seg["base_score"]
                    break

            merged = merge_multi_video_score(
                {"total": base_score, "base_total": base_score}, mv_result
            )
            scored_candidates.append(
                {
                    "candidate_key": candidate["candidate_id"],
                    "candidate": candidate,
                    "score": merged,
                    "score_total": merged["total"],
                    "duration_sec": round(
                        mv_result.get("meta", {}).get("total_duration", 0), 3
                    ),
                    "duration_bucket": get_duration_bucket(
                        mv_result.get("meta", {}).get("total_duration", 0),
                        settings.BATCH_DURATION_BUCKETS,
                    ),
                }
            )

        scored_candidates.sort(
            key=lambda x: (x["score_total"], x["duration_sec"]), reverse=True
        )
        phase_stats["candidate_score_sec"] = round(time.time() - start, 2)

        multi_dir = os.path.join(settings.BATCH_RESULTS_DIR, "multi_video")
        os.makedirs(multi_dir, exist_ok=True)

        selected_candidates = select_candidates_by_bucket(
            scored_candidates,
            target_count=getattr(settings, "BATCH_MULTI_VIDEO_TARGET_COUNT", 100),
            bucket_config=getattr(settings, "BATCH_DURATION_BUCKETS", []),
            score_threshold=getattr(settings, "BATCH_SCORE_THRESHOLD", None),
        )

        qualified_candidates = sum(
            1
            for item in selected_candidates
            if item["duration_sec"] >= settings.BATCH_MIN_MULTI_VIDEO_DURATION_SEC
        )

        top_candidates = []
        for item in selected_candidates[:20]:
            candidate = item["candidate"]
            score = item["score"]
            total_duration = sum(
                max(0, seg.get("end", 0) - seg.get("start", 0))
                for seg in candidate.get("segments", [])
            )
            video_ids = []
            for seg in candidate.get("segments", []):
                video_id = seg.get("video_id")
                if video_id and video_id not in video_ids:
                    video_ids.append(video_id)

            top_candidates.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "total_score": score["total"],
                    "base_total": score["base_total"],
                    "multi_video_score": score.get("multi_video"),
                    "segment_count": len(candidate.get("segments", [])),
                    "total_duration": round(total_duration, 2),
                    "video_ids": video_ids,
                    "segments": [
                        {
                            "video_id": seg.get("video_id"),
                            "start": seg.get("start"),
                            "end": seg.get("end"),
                            "text": seg.get("text"),
                        }
                        for seg in candidate.get("segments", [])
                    ],
                }
            )

        run_id = time.strftime("%Y%m%d_%H%M%S")
        summary = {
            "run_id": run_id,
            "total_candidates": len(scored_candidates),
            "selected_candidates": len(selected_candidates),
            "qualified_candidates": qualified_candidates,
            "min_duration_sec": settings.BATCH_MIN_MULTI_VIDEO_DURATION_SEC,
            "generation_target": getattr(settings, "BATCH_MULTI_VIDEO_TARGET_COUNT", 100),
            "duration_buckets": getattr(settings, "BATCH_DURATION_BUCKETS", []),
            "top_candidates": top_candidates,
            "source_videos": source_videos,
        }
        summary_path = os.path.join(multi_dir, "summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"[多视频] summary 已写出：{summary_path}", file=sys.stderr)

        # 生成高分多视频候选的实际视频文件
        video_generation_dir = os.path.join(multi_dir, "generated_videos", run_id)
        os.makedirs(video_generation_dir, exist_ok=True)

        # 准备视频源信息
        video_sources_map = {}
        for video_id, srt_path, mp4_path in videos_data:
            video_sources_map[video_id] = {"video_id": video_id, "video_path": mp4_path}

        sources_list = [
            video_sources_map[vid] for vid in source_videos if vid in video_sources_map
        ]

        # 为选中的多视频候选生成实际视频，且只允许生成满足最小时长要求的候选。
        generated_videos = []

        start = time.time()
        for item in selected_candidates:
            candidate = item["candidate"]
            score = item["score"]

            candidate_id = candidate["candidate_id"]
            segments = candidate.get("segments", [])
            total_duration = sum(
                max(0, seg.get("end", 0) - seg.get("start", 0)) for seg in segments
            )

            if not segments:
                continue
            if total_duration < settings.BATCH_MIN_MULTI_VIDEO_DURATION_SEC:
                print(
                    f"[多视频] 跳过候选 {candidate_id}: 总时长过短 ({round(total_duration, 2)}s)",
                    file=sys.stderr,
                )
                continue

            try:
                print(
                    f"[多视频] 正在生成候选 {candidate_id} (分数: {score['total']})...",
                    file=sys.stderr,
                )

                output_path = generate_multi_video(
                    sources_list, segments, video_generation_dir, candidate_id
                )

                generated_videos.append(
                    {
                        "candidate_id": candidate_id,
                        "output_path": output_path,
                        "score": score["total"],
                        "machine_score": score,
                        "segment_count": len(segments),
                        "total_duration": round(total_duration, 2),
                        "duration_bucket": get_duration_bucket(
                            total_duration, settings.BATCH_DURATION_BUCKETS
                        ),
                    }
                )

                print(f"[多视频] 已生成: {output_path}", file=sys.stderr)
            except Exception as e:
                print(f"[多视频] 生成候选 {candidate_id} 失败: {e}", file=sys.stderr)
                continue
        phase_stats["video_generate_sec"] = round(time.time() - start, 2)

        # 更新 summary.json，添加生成的视频信息
        summary["generated_videos"] = generated_videos
        summary["videos_generated"] = len(generated_videos)
        summary["generated_videos_dir"] = video_generation_dir
        summary["duration_requirement_met"] = len(generated_videos) > 0

        # 重新写入更新后的 summary
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}", file=sys.stderr)
        print(
            f"多视频组合流程完成，生成 {len(generated_videos)} 个视频", file=sys.stderr
        )
        print(f"{'=' * 60}", file=sys.stderr)
        total_duration_sec = round(time.time() - total_start, 2)
        logger.log_event(
            "multi_video_summary",
            total_duration_sec=total_duration_sec,
            source_video_count=len(source_videos),
            total_candidates=len(scored_candidates),
            videos_generated=len(generated_videos),
            summary_path=summary_path,
            **phase_stats,
        )
        print(f"[MULTI VIDEO TOTAL] {total_duration_sec} s", file=sys.stderr)
    finally:
        settings.BATCH_PHASE1_COUNT = old_phase1_count
        settings.BATCH_PHASE2_COUNT = old_phase2_count
        if getattr(settings, "BATCH_TEST_MODE", False):
            print(
                f"[多视频模式] 恢复参数：Phase1={old_phase1_count}, Phase2={old_phase2_count}",
                file=sys.stderr,
            )


def generate_summary(
    video_id,
    base_dir,
    phase1_files,
    phase2_files,
    phase3_results,
    candidate_infos,
    selected_candidates,
    generated,
):
    """生成统计报告"""
    top_scores = sorted(
        candidate_infos,
        key=lambda item: (item["score_total"], item["duration_sec"]),
        reverse=True,
    )[:10]
    summary = {
        "video_id": video_id,
        "phase1_count": len(phase1_files),
        "phase2_count": len(phase2_files),
        "phase3_success": len(phase3_results),
        "phase4_scored": len(candidate_infos),
        "phase5_generated": len(generated),
        "generated_videos": generated,
        "generation_target": getattr(settings, "BATCH_SINGLE_VIDEO_TARGET_PER_SOURCE", 10),
        "selected_candidate_count": len(selected_candidates),
        "duration_buckets": getattr(settings, "BATCH_DURATION_BUCKETS", []),
        "visual_enabled": getattr(settings, "BATCH_VISUAL_ENABLE", False),
        "transition_enabled": getattr(settings, "BATCH_TRANSITION_ENABLE", False),
        "top_scores": [
            {
                "idx": item["idx"],
                "duration_sec": round(item["duration_sec"], 3),
                "duration_bucket": item["duration_bucket"],
                "total": item["score"].get("total"),
                "base_total": item["score"].get("base_total"),
                "video": item["score"].get("video"),
                "transition": item["score"].get("transition"),
                "audio": item["score"].get("audio"),
                "visual": item["score"].get("visual"),
                "transition_natural": item["score"].get("transition_natural"),
            }
            for item in top_scores
        ],
    }
    summary_path = os.path.join(base_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    total_start = time.time()
    logger = BatchLogger(settings.BATCH_LOG_FILE)
    videos = scan_videos(settings.DATA_DIR)
    print(f"扫描到 {len(videos)} 个视频", file=sys.stderr)

    if getattr(settings, "BATCH_MULTI_VIDEO_ENABLE", False) and len(videos) >= 2:
        print(
            f"\n[多视频模式] 检测到 {len(videos)} 个视频，启动多视频组合流程",
            file=sys.stderr,
        )
        process_multi_video(videos, logger)
    else:
        for video_id, srt_path, mp4_path in videos:
            try:
                process_video(video_id, srt_path, mp4_path, logger)
            except Exception as e:
                print(f"[错误] 处理视频 {video_id} 时出错：{e}", file=sys.stderr)
                continue

    print(f"\n{'=' * 60}", file=sys.stderr)
    print("批量生成完成", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)
    total_duration_sec = round(time.time() - total_start, 2)
    logger.log_event(
        "batch_run_summary",
        total_duration_sec=total_duration_sec,
        video_count=len(videos),
        multi_video_enabled=getattr(settings, "BATCH_MULTI_VIDEO_ENABLE", False),
    )
    print(f"[BATCH TOTAL] {total_duration_sec} s", file=sys.stderr)


if __name__ == "__main__":
    main()
