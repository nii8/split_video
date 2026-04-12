import os
import sys
import json
import time
import settings
from batch.logger import BatchLogger
from batch.phase_runner import run_phase1_loop, run_phase2_loop, run_phase3_loop
from batch.evaluator import evaluate_quality
from batch.visual_scorer import enrich_top_interval_candidates_with_visual_score
from batch.transition_scorer import enrich_candidates_with_transition_score
from batch.multi_video_selector import build_video_sources, get_main_video
from batch.video_pool_builder import keep_intervals_to_segments
from batch.video_combiner import build_multi_video_candidates
from batch.multi_video_scorer import (
    score_multi_video_candidate,
    merge_multi_video_score,
)
from make_video.step3 import cut_video_main
from make_video.multi_video_builder import generate_multi_video


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
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"开始处理视频 {video_id}", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)

    base_dir = os.path.join(settings.BATCH_RESULTS_DIR, video_id)

    # Phase1: 多次字幕筛选
    phase1_dir = os.path.join(base_dir, "phase1")
    phase1_files = run_phase1_loop(
        video_id, srt_path, phase1_dir, settings.BATCH_PHASE1_COUNT, logger
    )
    if not phase1_files:
        print(f"[错误] Phase1 全部失败，跳过视频 {video_id}", file=sys.stderr)
        return

    # Phase2: 多次脚本生成
    phase2_dir = os.path.join(base_dir, "phase2")
    phase2_files = run_phase2_loop(
        video_id, phase1_files, phase2_dir, settings.BATCH_PHASE2_COUNT, logger
    )
    if not phase2_files:
        print(f"[错误] Phase2 全部失败，跳过视频 {video_id}", file=sys.stderr)
        return

    # Phase3: 时间轴匹配
    phase3_dir = os.path.join(base_dir, "phase3")
    phase3_results = run_phase3_loop(
        video_id, srt_path, phase2_files, phase3_dir, logger
    )
    if not phase3_results:
        print("[警告] Phase3 全部失败，没有有效时间序列", file=sys.stderr)
        return

    # Phase4: 先按原来的规则做一轮基础评分
    phase4_dir = os.path.join(base_dir, "phase4")
    os.makedirs(phase4_dir, exist_ok=True)
    scored = []
    for idx, intervals in phase3_results:
        start = time.time()
        score = evaluate_quality(mp4_path, intervals)
        duration = time.time() - start
        score_path = os.path.join(phase4_dir, f"score_{idx:03d}.json")
        with open(score_path, "w", encoding="utf-8") as f:
            json.dump(score, f, ensure_ascii=False, indent=2)
        logger.log_phase(
            video_id, "phase4", idx, duration, "success", total_score=score["total"]
        )
        scored.append((idx, intervals, score))

    # 第一阶段新增：
    # 这里只给前几个候选补一层视觉评分，不改原来的主流程。
    if getattr(settings, "BATCH_VISUAL_ENABLE", False) and scored:
        visual_dir = os.path.join(base_dir, "visual")
        os.makedirs(visual_dir, exist_ok=True)
        scored = enrich_top_interval_candidates_with_visual_score(
            video_id,
            mp4_path,
            scored,
            visual_dir,
            logger=logger,
            top_n=getattr(settings, "BATCH_VISUAL_TOPN", 2),
            use_llm=getattr(settings, "BATCH_VISUAL_USE_LLM", False),
        )

    # 第二阶段最小版：
    # 先不用多模态切点评分，只按 intervals 规则判断“是不是太碎、太跳”。
    if getattr(settings, "BATCH_TRANSITION_ENABLE", False) and scored:
        scored = enrich_candidates_with_transition_score(scored)

    # Phase5: 分数够高的候选再去生成视频
    phase5_dir = os.path.join(base_dir, "phase5")
    os.makedirs(phase5_dir, exist_ok=True)
    generated = []
    for idx, intervals, score in scored:
        if score["total"] >= settings.BATCH_SCORE_THRESHOLD:
            start = time.time()
            try:
                output_path = cut_video_main(intervals, mp4_path, video_id, "batch")
                final_path = os.path.join(phase5_dir, f"video_{idx:03d}.mp4")
                os.rename(output_path, final_path)
                duration = time.time() - start
                logger.log_phase(
                    video_id, "phase5", idx, duration, "success", output=final_path
                )
                generated.append(final_path)
            except Exception as e:
                duration = time.time() - start
                logger.log_phase(
                    video_id, "phase5", idx, duration, "failed", reason=str(e)
                )

    generate_summary(
        video_id,
        base_dir,
        phase1_files,
        phase2_files,
        phase3_results,
        scored,
        generated,
    )
    print(
        f"[完成] 视频 {video_id} 处理完成，生成 {len(generated)} 个视频",
        file=sys.stderr,
    )


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
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"开始多视频组合流程，共 {len(videos_data)} 个视频", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)

    old_phase1_count = settings.BATCH_PHASE1_COUNT
    old_phase2_count = settings.BATCH_PHASE2_COUNT
    if getattr(settings, "BATCH_TEST_MODE", False):
        settings.BATCH_PHASE1_COUNT = 1
        settings.BATCH_PHASE2_COUNT = 1
        print(f"[多视频模式] 临时降低参数：Phase1=1, Phase2=1", file=sys.stderr)

    try:
        per_video_results = []
        source_videos = []

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

        if not per_video_results:
            print("[错误] 所有视频都没有有效片段，跳过", file=sys.stderr)
            return

        pools = {}
        for result in per_video_results:
            video_id = result["video_id"]
            pools[video_id] = {
                "video_id": video_id,
                "segments": result["segments"],
                "total_segments": len(result["segments"]),
            }
            print(
                f"[多视频池] {video_id}: {len(result['segments'])} 个片段", file=sys.stderr
            )

        candidates = build_multi_video_candidates(pools, max_candidates=20)
        print(f"[多视频] 生成 {len(candidates)} 个组合候选", file=sys.stderr)

        if not candidates:
            print("[错误] 没有生成有效候选，跳过", file=sys.stderr)
            return

        scored_candidates = []
        for candidate in candidates:
            mv_result = score_multi_video_candidate(candidate)
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
                    "candidate": candidate,
                    "score": merged,
                }
            )

        scored_candidates.sort(key=lambda x: x["score"]["total"], reverse=True)

        multi_dir = os.path.join(settings.BATCH_RESULTS_DIR, "multi_video")
        os.makedirs(multi_dir, exist_ok=True)

        top_candidates = []
        for item in scored_candidates[:5]:
            candidate = item["candidate"]
            score = item["score"]
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

        summary = {
            "total_candidates": len(scored_candidates),
            "top_candidates": top_candidates,
            "source_videos": source_videos,
        }
        summary_path = os.path.join(multi_dir, "summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"[多视频] summary 已写出：{summary_path}", file=sys.stderr)

        # 生成高分多视频候选的实际视频文件
        video_generation_dir = os.path.join(multi_dir, "generated_videos")
        os.makedirs(video_generation_dir, exist_ok=True)

        # 准备视频源信息
        video_sources_map = {}
        for video_id, srt_path, mp4_path in videos_data:
            video_sources_map[video_id] = {
                "video_id": video_id,
                "video_path": mp4_path
            }

        sources_list = [video_sources_map[vid] for vid in source_videos if vid in video_sources_map]

        # 为top N个候选生成实际视频（避免生成过多文件）
        top_n_generate = 5  # 可以根据设置调整
        generated_videos = []

        for i, item in enumerate(scored_candidates[:top_n_generate]):
            candidate = item["candidate"]
            score = item["score"]

            if score["total"] >= settings.BATCH_SCORE_THRESHOLD:
                candidate_id = candidate["candidate_id"]
                segments = candidate.get("segments", [])

                if not segments:
                    continue

                try:
                    print(f"[多视频] 正在生成候选 {candidate_id} (分数: {score['total']})...", file=sys.stderr)

                    # 生成多视频文件
                    output_path = generate_multi_video(
                        sources_list,
                        segments,
                        video_generation_dir,
                        candidate_id
                    )

                    generated_videos.append({
                        "candidate_id": candidate_id,
                        "output_path": output_path,
                        "score": score["total"],
                        "segment_count": len(segments)
                    })

                    print(f"[多视频] 已生成: {output_path}", file=sys.stderr)
                except Exception as e:
                    print(f"[多视频] 生成候选 {candidate_id} 失败: {e}", file=sys.stderr)
                    continue

        # 更新 summary.json，添加生成的视频信息
        summary["generated_videos"] = generated_videos
        summary["videos_generated"] = len(generated_videos)

        # 重新写入更新后的 summary
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}", file=sys.stderr)
        print(f"多视频组合流程完成，生成 {len(generated_videos)} 个视频", file=sys.stderr)
        print(f"{'=' * 60}", file=sys.stderr)
    finally:
        settings.BATCH_PHASE1_COUNT = old_phase1_count
        settings.BATCH_PHASE2_COUNT = old_phase2_count
        if getattr(settings, "BATCH_TEST_MODE", False):
            print(
                f"[多视频模式] 恢复参数：Phase1={old_phase1_count}, Phase2={old_phase2_count}",
                file=sys.stderr,
            )


def generate_summary(
    video_id, base_dir, phase1_files, phase2_files, phase3_results, scored, generated
):
    """生成统计报告"""
    top_scores = sorted(scored, key=lambda x: x[2]["total"], reverse=True)[:5]
    summary = {
        "video_id": video_id,
        "phase1_count": len(phase1_files),
        "phase2_count": len(phase2_files),
        "phase3_success": len(phase3_results),
        "phase4_scored": len(scored),
        "phase5_generated": len(generated),
        "generated_videos": generated,
        "visual_enabled": getattr(settings, "BATCH_VISUAL_ENABLE", False),
        "transition_enabled": getattr(settings, "BATCH_TRANSITION_ENABLE", False),
        "top_scores": [
            {
                "idx": idx,
                "total": score.get("total"),
                "base_total": score.get("base_total"),
                "visual": score.get("visual"),
                "transition_natural": score.get("transition_natural"),
            }
            for idx, _, score in top_scores
        ],
    }
    summary_path = os.path.join(base_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
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


if __name__ == "__main__":
    main()
