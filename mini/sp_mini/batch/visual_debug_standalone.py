"""
独立调试第一阶段视觉评分。

这个脚本不依赖 settings.py。
只要给视频路径、时间区间和 API Key，就能单独测试：
1. 抽帧
2. 拼 9 宫格
3. 调多模态模型打分
"""

import argparse
import base64
import json
import os
import re
import sys

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from batch.frame_sampler import sample_frames_for_interval, srt_time_to_seconds
from batch.image_grid import make_grid_image


def image_path_to_data_url(image_path):
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg"
    if ext == ".png":
        mime = "image/png"
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_visual_review_prompt():
    return (
        "请根据这张 9 宫格画面，对短视频出镜质量评分。\n"
        "评分维度：光线、清晰度、人脸可见性、表情感染力、肢体动作或姿态自然度、构图与背景整洁度、整体视觉吸引力。\n"
        "分数范围：0 到 10，可以保留 1 位小数。\n"
        "请特别关注是否适合做人物出镜短视频片段，而不是只判断图像是否存在。\n"
        "如果存在明显问题，请写入 issues 数组，issues 使用英文短标签，例如：dark_lighting、blur、no_face、weak_expression、messy_background、awkward_pose。\n"
        "严格只输出 JSON，格式如下：\n"
        "{\"score\": 8.2, \"summary\": \"一句中文总结\", \"issues\": [\"weak_expression\"]}"
    )


def parse_visual_score_response(response_text):
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
            "raw_text": text,
        }

    return {
        "score": 5.0,
        "summary": text[:120] if text else "模型未返回标准 JSON",
        "issues": [],
        "raw_text": text,
    }


def call_visual_llm(api_key, base_url, model, timeout, grid_image_path):
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "你是一名严格的视频视觉质检员，负责评估短视频素材的出镜质量。请只输出 JSON，不要输出额外解释。",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_visual_review_prompt()},
                    {"type": "image_url", "image_url": {"url": image_path_to_data_url(grid_image_path)}},
                ],
            },
        ],
        stream=False,
    )
    return parse_visual_score_response(response.choices[0].message.content)


def main():
    parser = argparse.ArgumentParser(description="脱离 settings.py 的视觉评分独立调试脚本")
    parser.add_argument("--video_path", required=True)
    parser.add_argument("--start", required=True, help="SRT 格式起始时间，如 00:00:10,000")
    parser.add_argument("--end", required=True, help="SRT 格式结束时间，如 00:00:28,000")
    parser.add_argument("--api_key", required=True)
    parser.add_argument("--base_url", default="https://coding.dashscope.aliyuncs.com/v1")
    parser.add_argument("--model", default="qwen-vl-max")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--sample_every_sec", type=int, default=2)
    parser.add_argument("--max_frames", type=int, default=9)
    parser.add_argument("--work_dir", default="./data/batch_results/visual_debug_standalone")
    args = parser.parse_args()

    os.makedirs(args.work_dir, exist_ok=True)
    frames_dir = os.path.join(args.work_dir, "frames")
    start_sec = srt_time_to_seconds(args.start)
    end_sec = srt_time_to_seconds(args.end)

    image_paths = sample_frames_for_interval(
        args.video_path,
        start_sec,
        end_sec,
        sample_every_sec=args.sample_every_sec,
        output_dir=frames_dir,
        max_frames_per_interval=args.max_frames,
    )
    if not image_paths:
        raise RuntimeError("没有抽到任何图片，请检查视频路径和时间区间")

    grid_path = os.path.join(args.work_dir, "grid.jpg")
    make_grid_image(image_paths, grid_path)
    result = call_visual_llm(args.api_key, args.base_url, args.model, args.timeout, grid_path)
    output = {
        "video_path": args.video_path,
        "start": args.start,
        "end": args.end,
        "grid_path": grid_path,
        "frame_count": len(image_paths),
        "result": result,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
