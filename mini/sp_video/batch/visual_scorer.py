"""
第一阶段：视觉评分。

当前只做最小版本：
1. 对 interval 抽帧
2. 拼成固定 9 宫格
3. 调多模态模型打分
4. 把视觉分并回原来的候选分数

这里故意保留过程式写法。
后续如果要修模型名、prompt、返回格式，主要改 call_visual_llm() 和 parse_visual_score_response()。
"""

import base64
import json
import os
import re
import time

import settings
from openai import OpenAI

from batch.frame_sampler import sample_frames_for_intervals
from batch.image_grid import make_grid_image


def score_candidate_visual(video_id, candidate_id, video_path, intervals, work_dir, use_llm=False):
    """对一个候选视频整体做视觉评分"""
    frames_dir = os.path.join(work_dir, "frames", candidate_id)
    grids_dir = os.path.join(work_dir, "grids")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(grids_dir, exist_ok=True)

    grouped_frames = sample_frames_for_intervals(
        video_path,
        intervals,
        output_dir=frames_dir,
        sample_every_sec=settings.BATCH_VISUAL_SAMPLE_EVERY_SEC,
        max_frames_per_interval=settings.BATCH_VISUAL_MAX_FRAMES,
    )

    windows = []
    frame_sampling_duration_sec = round(sum(item.get("ffmpeg_duration_sec", 0) for item in grouped_frames), 2)
    grid_duration_sec = 0.0
    llm_duration_sec = 0.0
    for item in grouped_frames:
        if not item["image_paths"]:
            continue
        grid_path = os.path.join(grids_dir, f"{candidate_id}_interval_{item['interval_index']:03d}.jpg")
        grid_start = time.time()
        make_grid_image(item["image_paths"], grid_path)
        grid_duration_sec += time.time() - grid_start
        # 第一阶段先保留两种模式：
        # 1. fake：本地没模型时先打通流程
        # 2. llm：真实多模态评分
        llm_start = time.time()
        score_result = call_visual_llm(grid_path) if use_llm else fake_visual_score(item)
        llm_duration_sec += time.time() - llm_start
        score_result["interval_index"] = item["interval_index"]
        score_result["grid_path"] = grid_path
        windows.append(score_result)

    if windows:
        visual_score = round(sum(item["score"] for item in windows) / len(windows), 2)
    else:
        visual_score = 0.0

    return {
        "video_id": video_id,
        "candidate_id": candidate_id,
        "visual_score": visual_score,
        "frame_sampling_duration_sec": frame_sampling_duration_sec,
        "grid_duration_sec": round(grid_duration_sec, 2),
        "llm_duration_sec": round(llm_duration_sec, 2),
        "windows": windows,
    }


def score_interval_visual(video_id, candidate_id, video_path, interval_item, work_dir, use_llm=False):
    """对单个 interval 做抽帧、拼图、评分，便于独立调试"""
    return score_candidate_visual(video_id, candidate_id, video_path, [interval_item], work_dir, use_llm=use_llm)


def fake_visual_score(item):
    """先用假评分打通流程，后续环境正常后再切到真实模型"""
    frame_count = len(item.get("image_paths", []))
    duration = item.get("end_sec", 0) - item.get("start_sec", 0)

    score = 6.0
    if frame_count >= 6:
        score += 1.0
    if 4 <= duration <= 18:
        score += 1.0
    if frame_count >= 9:
        score += 0.5

    return {
        "score": round(min(score, 9.0), 2),
        "summary": "按抽帧数量和片段时长给基础视觉分",
        "issues": [],
        "mode": "fake",
    }


def call_visual_llm(grid_image_path):
    """调用多模态模型给 9 宫格图做视觉评分"""
    if not settings.BAILIAN_API_KEY:
        raise ValueError("未配置 BAILIAN_API_KEY，无法调用视觉评分模型")

    model_name = getattr(settings, "BATCH_VISUAL_MODEL", "qwen-vl-max")
    timeout = getattr(settings, "BATCH_VISUAL_TIMEOUT", 120)
    prompt = build_visual_review_prompt()
    data_url = image_path_to_data_url(grid_image_path)

    client = OpenAI(
        api_key=settings.BAILIAN_API_KEY,
        base_url="https://coding.dashscope.aliyuncs.com/v1",
        timeout=timeout,
    )
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "你是一名严格的视频视觉质检员，负责评估短视频素材的出镜质量。请只输出 JSON，不要输出额外解释。",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        stream=False,
    )
    return parse_visual_score_response(response.choices[0].message.content)


def build_visual_review_prompt():
    # prompt 固定，不做太多模板化，方便后续人直接改。
    return (
        "请根据这张 9 宫格画面，对短视频出镜质量评分。\n"
        "评分维度：光线、清晰度、人脸可见性、表情感染力、肢体动作/姿态自然度、构图与背景整洁度、整体视觉吸引力。\n"
        "分数范围：0 到 10，可以保留 1 位小数。\n"
        "请特别关注是否适合做人物出镜短视频片段，而不是只判断图像是否存在。\n"
        "如果存在明显问题，请写入 issues 数组，issues 使用英文短标签，例如：dark_lighting、blur、no_face、weak_expression、messy_background、awkward_pose。\n"
        "严格只输出 JSON，格式如下：\n"
        "{\"score\": 8.2, \"summary\": \"一句中文总结\", \"issues\": [\"weak_expression\"]}"
    )


def image_path_to_data_url(image_path):
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg"
    if ext == ".png":
        mime = "image/png"
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def parse_visual_score_response(response_text):
    """把模型输出解析成结构化结果"""
    text = str(response_text).strip()
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None

    if parsed is None:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = None

    if parsed is not None:
        score = parsed.get("score", 5.0)
        try:
            score = float(score)
        except Exception:
            score = 5.0
        issues = parsed.get("issues", [])
        if not isinstance(issues, list):
            issues = [str(issues)]
        return {
            "score": max(0.0, min(round(score, 2), 10.0)),
            "summary": str(parsed.get("summary", "")).strip(),
            "issues": [str(item) for item in issues],
            "mode": "llm",
            "raw_text": text,
        }

    return {
        "score": 5.0,
        "summary": text[:120] if text else "模型未返回标准 JSON",
        "issues": [],
        "mode": "llm_fallback",
        "raw_text": text,
    }


def save_visual_scores(score_path, data):
    os.makedirs(os.path.dirname(score_path), exist_ok=True) if os.path.dirname(score_path) else None
    with open(score_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_interval_and_visual_score(score, visual_result, visual_weight=0.2):
    """把 visual_score 合并进总分"""
    merged = dict(score)
    merged["visual"] = round(visual_result["visual_score"], 2)
    merged["base_total"] = round(score["total"], 2)
    merged["total"] = round(score["total"] * (1 - visual_weight) + visual_result["visual_score"] * visual_weight, 2)
    return merged


def enrich_top_interval_candidates_with_visual_score(video_id, video_path, scored_candidates, work_dir, logger=None, top_n=2, use_llm=False):
    """只对前几个候选补视觉评分"""
    if not scored_candidates:
        return scored_candidates

    # 先按原分排序，只补前几个候选的视觉分，避免第一阶段成本太高。
    ranked = sorted(scored_candidates, key=lambda x: x[2]["total"], reverse=True)
    visual_map = {}

    for idx, intervals, score in ranked[:top_n]:
        start = time.time()
        visual_result = score_candidate_visual(
            video_id,
            f"candidate_{idx:03d}",
            video_path,
            intervals,
            work_dir,
            use_llm=use_llm,
        )
        duration = time.time() - start
        visual_map[idx] = visual_result
        if logger:
            logger.log_phase(
                video_id,
                "visual",
                idx,
                duration,
                "success",
                visual_score=visual_result["visual_score"],
                frame_sampling_duration_sec=visual_result["frame_sampling_duration_sec"],
                grid_duration_sec=visual_result["grid_duration_sec"],
                llm_duration_sec=visual_result["llm_duration_sec"],
            )

    merged = []
    for idx, intervals, score in scored_candidates:
        if idx in visual_map:
            merged_score = merge_interval_and_visual_score(score, visual_map[idx])
            merged.append((idx, intervals, merged_score))
        else:
            merged.append((idx, intervals, score))

    save_visual_scores(os.path.join(work_dir, "visual_scores.json"), {
        "video_id": video_id,
        "results": list(visual_map.values()),
    })
    return merged
