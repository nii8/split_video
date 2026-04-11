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
from make_video.step3 import cut_video_main


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


def process_video(video_id, srt_path, mp4_path, logger):
    """处理单个视频的完整流程"""
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"开始处理视频 {video_id}", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)

    base_dir = os.path.join(settings.BATCH_RESULTS_DIR, video_id)

    # Phase1: 多次字幕筛选
    phase1_dir = os.path.join(base_dir, "phase1")
    phase1_files = run_phase1_loop(video_id, srt_path, phase1_dir, settings.BATCH_PHASE1_COUNT, logger)
    if not phase1_files:
        print(f"[错误] Phase1 全部失败，跳过视频 {video_id}", file=sys.stderr)
        return

    # Phase2: 多次脚本生成
    phase2_dir = os.path.join(base_dir, "phase2")
    phase2_files = run_phase2_loop(video_id, phase1_files, phase2_dir, settings.BATCH_PHASE2_COUNT, logger)
    if not phase2_files:
        print(f"[错误] Phase2 全部失败，跳过视频 {video_id}", file=sys.stderr)
        return

    # Phase3: 时间轴匹配
    phase3_dir = os.path.join(base_dir, "phase3")
    phase3_results = run_phase3_loop(video_id, srt_path, phase2_files, phase3_dir, logger)
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
        logger.log_phase(video_id, "phase4", idx, duration, "success", total_score=score["total"])
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
                logger.log_phase(video_id, "phase5", idx, duration, "success", output=final_path)
                generated.append(final_path)
            except Exception as e:
                duration = time.time() - start
                logger.log_phase(video_id, "phase5", idx, duration, "failed", reason=str(e))

    generate_summary(video_id, base_dir, phase1_files, phase2_files, phase3_results, scored, generated)
    print(f"[完成] 视频 {video_id} 处理完成，生成 {len(generated)} 个视频", file=sys.stderr)


def generate_summary(video_id, base_dir, phase1_files, phase2_files, phase3_results, scored, generated):
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
        ]
    }
    summary_path = os.path.join(base_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    logger = BatchLogger(settings.BATCH_LOG_FILE)
    videos = scan_videos(settings.DATA_DIR)
    print(f"扫描到 {len(videos)} 个视频", file=sys.stderr)

    for video_id, srt_path, mp4_path in videos:
        try:
            process_video(video_id, srt_path, mp4_path, logger)
        except Exception as e:
            print(f"[错误] 处理视频 {video_id} 时出错: {e}", file=sys.stderr)
            continue

    print(f"\n{'=' * 60}", file=sys.stderr)
    print("批量生成完成", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)


if __name__ == "__main__":
    main()
