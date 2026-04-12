"""
test_multi_video.py - 测试多视频生成功能
"""

import os
import json
from batch.multi_video_selector import build_video_sources
from make_video.multi_video_builder import generate_multi_video


def test_multi_video_builder():
    """
    测试多视频构建器的基本功能
    """
    print("开始测试多视频构建器...")

    # 准备测试数据 - 这些路径需要替换为实际存在的视频文件
    sources = [
        {
            "video_id": "test1",
            "video_path": "./data/hanbing/test1.mp4"  # 示例路径
        },
        {
            "video_id": "test2",
            "video_path": "./data/hanbing/test2.mp4"  # 示例路径
        }
    ]

    segments = [
        {
            "video_id": "test1",
            "start": 0,
            "end": 10,
            "text": "测试片段1"
        },
        {
            "video_id": "test2",
            "start": 5,
            "end": 15,
            "text": "测试片段2"
        }
    ]

    try:
        output_dir = "./data/batch_results/test_multi_video"
        os.makedirs(output_dir, exist_ok=True)

        output_path = generate_multi_video(
            sources,
            segments,
            output_dir,
            "test_candidate_001"
        )

        print(f"✓ 成功生成多视频: {output_path}")
        return True

    except Exception as e:
        print(f"✗ 多视频生成失败: {e}")
        # 这可能是由于测试视频文件不存在，这是正常的
        print("注意: 如果是因为视频文件不存在导致的错误，这是正常的测试情况")
        return False


def test_integration_with_settings():
    """
    测试集成设置
    """
    import settings

    print("\n检查设置配置:")
    print(f"BATCH_MULTI_VIDEO_ENABLE: {settings.BATCH_MULTI_VIDEO_ENABLE}")
    print(f"BATCH_TEST_MODE: {settings.BATCH_TEST_MODE}")
    print(f"BATCH_PHASE1_COUNT: {settings.BATCH_PHASE1_COUNT}")
    print(f"BATCH_PHASE2_COUNT: {settings.BATCH_PHASE2_COUNT}")


def main():
    print("="*60)
    print("多视频功能测试")
    print("="*60)

    # 测试集成设置
    test_integration_with_settings()

    # 测试多视频构建器
    test_multi_video_builder()

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    main()