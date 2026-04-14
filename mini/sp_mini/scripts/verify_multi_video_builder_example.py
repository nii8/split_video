"""
verify_multi_video_builder_example.py

示例脚本：手动验证 multi_video_builder 的本地调用方式。

注意：
- 这是示例脚本，不是正式测试。
- 运行前必须先把 sources 中的路径替换成真实存在的视频文件。
- 该脚本只验证 FFmpeg 多输入拼接链路，不代表完整 batch_generator 主流程已经验收通过。
"""

import os

from make_video.multi_video_builder import generate_multi_video


def main():
    print("开始运行多视频 builder 示例验证...")

    sources = [
        {
            "video_id": "example1",
            "video_path": "./data/hanbing/example1/example1.mp4",
        },
        {
            "video_id": "example2",
            "video_path": "./data/hanbing/example2/example2.mp4",
        },
    ]

    segments = [
        {
            "video_id": "example1",
            "start": 0,
            "end": 3,
            "text": "示例片段1",
        },
        {
            "video_id": "example2",
            "start": 1,
            "end": 4,
            "text": "示例片段2",
        },
    ]

    missing_paths = [src["video_path"] for src in sources if not os.path.exists(src["video_path"])]
    if missing_paths:
        print("未运行：请先把示例路径替换成真实文件。")
        for path in missing_paths:
            print(f"缺失文件: {path}")
        return

    output_dir = "./data/batch_results/manual_verify_multi_video"
    os.makedirs(output_dir, exist_ok=True)

    output_path = generate_multi_video(
        sources,
        segments,
        output_dir,
        "manual_verify_001",
    )
    print(f"生成完成: {output_path}")


if __name__ == "__main__":
    main()
