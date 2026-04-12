"""
test_batch_generator.py - 批量生成器集成测试

测试单视频模式和多视频模式的完整流程
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import shutil

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import settings
from batch_generator import scan_videos, process_video, process_multi_video
from batch.logger import BatchLogger
from make_video.multi_video_builder import generate_multi_video


class TestSingleVideoMode:
    """单视频模式测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        # 保存原始配置
        self.original_multi_video = settings.BATCH_MULTI_VIDEO_ENABLE
        self.original_test_mode = settings.BATCH_TEST_MODE
        self.original_phase1 = settings.BATCH_PHASE1_COUNT
        self.original_phase2 = settings.BATCH_PHASE2_COUNT

        # 设置为测试模式
        settings.BATCH_MULTI_VIDEO_ENABLE = False
        settings.BATCH_TEST_MODE = True
        settings.BATCH_PHASE1_COUNT = 1
        settings.BATCH_PHASE2_COUNT = 1

        yield

        # 恢复原始配置
        settings.BATCH_MULTI_VIDEO_ENABLE = self.original_multi_video
        settings.BATCH_TEST_MODE = self.original_test_mode
        settings.BATCH_PHASE1_COUNT = self.original_phase1
        settings.BATCH_PHASE2_COUNT = self.original_phase2

    def test_scan_videos(self):
        """测试视频扫描功能"""
        videos = scan_videos(settings.DATA_DIR)
        assert len(videos) >= 1, "Should find at least 1 video"

        # 验证返回格式
        for video_id, srt_path, mp4_path in videos:
            assert os.path.exists(srt_path), f"SRT file should exist: {srt_path}"
            assert os.path.exists(mp4_path), f"MP4 file should exist: {mp4_path}"

    def test_video_file_validity(self):
        """测试视频文件有效性"""
        videos = scan_videos(settings.DATA_DIR)
        assert len(videos) >= 1

        for video_id, srt_path, mp4_path in videos:
            # 使用 ffprobe 验证视频文件
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    mp4_path,
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Video file should be valid: {mp4_path}"

            duration = float(result.stdout.strip())
            assert duration > 0, f"Video should have positive duration: {mp4_path}"


class TestMultiVideoMode:
    """多视频模式测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.original_multi_video = settings.BATCH_MULTI_VIDEO_ENABLE
        self.original_test_mode = settings.BATCH_TEST_MODE
        self.original_phase1 = settings.BATCH_PHASE1_COUNT
        self.original_phase2 = settings.BATCH_PHASE2_COUNT

        # 设置为多视频测试模式
        settings.BATCH_MULTI_VIDEO_ENABLE = True
        settings.BATCH_TEST_MODE = True
        settings.BATCH_PHASE1_COUNT = 1
        settings.BATCH_PHASE2_COUNT = 1

        yield

        # 恢复原始配置
        settings.BATCH_MULTI_VIDEO_ENABLE = self.original_multi_video
        settings.BATCH_TEST_MODE = self.original_test_mode
        settings.BATCH_PHASE1_COUNT = self.original_phase1
        settings.BATCH_PHASE2_COUNT = self.original_phase2

    def test_multi_video_requires_multiple_sources(self):
        """测试多视频模式需要多个视频源"""
        videos = scan_videos(settings.DATA_DIR)
        # 多视频模式需要至少 2 个视频
        assert len(videos) >= 2, "Multi-video mode requires at least 2 videos"

    def test_video_sources_format(self):
        """测试视频源格式"""
        from batch.multi_video_selector import build_video_sources

        videos = scan_videos(settings.DATA_DIR)
        sources = build_video_sources(videos)

        assert len(sources) >= 2, "Should have at least 2 sources"

        for source in sources:
            assert "video_id" in source, "Source should have video_id"
            assert "video_path" in source, "Source should have video_path"
            assert os.path.exists(source["video_path"]), f"Video path should exist"


class TestMultiVideoBuilder:
    """多视频构建器测试"""

    @pytest.fixture
    def test_videos(self):
        """获取测试视频"""
        videos = scan_videos(settings.DATA_DIR)
        # 返回前两个视频
        return videos[:2] if len(videos) >= 2 else videos

    def test_generate_multi_video(self, test_videos):
        """测试多视频生成"""
        if len(test_videos) < 2:
            pytest.skip("Need at least 2 videos for multi-video test")

        # 准备数据
        sources = [
            {"video_id": test_videos[0][0], "video_path": test_videos[0][2]},
            {"video_id": test_videos[1][0], "video_path": test_videos[1][2]},
        ]

        segments = [
            {"video_id": test_videos[0][0], "start": 0, "end": 3, "text": "片段 1"},
            {"video_id": test_videos[1][0], "start": 0, "end": 3, "text": "片段 2"},
        ]

        # 创建临时输出目录
        output_dir = tempfile.mkdtemp()

        try:
            # 生成视频
            output_path = generate_multi_video(
                sources, segments, output_dir, "test_001"
            )

            # 验证输出
            assert os.path.exists(output_path), (
                f"Output file should exist: {output_path}"
            )

            # 验证视频有效性
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration,size",
                    "-show_entries",
                    "stream=codec_type,codec_name",
                    "-of",
                    "json",
                    output_path,
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, "Generated video should be valid"

            data = json.loads(result.stdout)
            assert "streams" in data, "Should have streams"
            assert "format" in data, "Should have format"

            # 验证有视频和音频流
            stream_types = [s["codec_type"] for s in data["streams"]]
            assert "video" in stream_types, "Should have video stream"
            assert "audio" in stream_types, "Should have audio stream"

            # 验证时长
            duration = float(data["format"]["duration"])
            assert duration > 0, "Video should have positive duration"
            assert duration <= 10, "Test video should be short (<= 10s)"

        finally:
            # 清理
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_multi_video_from_multiple_sources(self, test_videos):
        """测试从多个视频源生成"""
        if len(test_videos) < 2:
            pytest.skip("Need at least 2 videos for multi-video test")

        sources = [{"video_id": v[0], "video_path": v[2]} for v in test_videos[:2]]

        # 每个视频取一个片段
        segments = []
        for i, video in enumerate(test_videos[:2]):
            segments.append(
                {
                    "video_id": video[0],
                    "start": 1,  # 从 1 秒开始
                    "end": 4,  # 到 4 秒结束
                    "text": f"片段{i + 1}",
                }
            )

        output_dir = tempfile.mkdtemp()

        try:
            output_path = generate_multi_video(
                sources, segments, output_dir, "test_multi_001"
            )

            assert os.path.exists(output_path)

            # 验证时长应该是两个片段之和（约 6 秒）
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    output_path,
                ],
                capture_output=True,
                text=True,
            )
            duration = float(result.stdout.strip())

            # 允许一定误差
            assert 5.0 <= duration <= 8.0, (
                f"Duration should be around 6s, got {duration}s"
            )

        finally:
            shutil.rmtree(output_dir, ignore_errors=True)


class TestConfiguration:
    """配置测试"""

    def test_multi_video_enable_flag(self):
        """测试多视频开关配置"""
        # 验证配置存在
        assert hasattr(settings, "BATCH_MULTI_VIDEO_ENABLE")

        # 验证类型
        assert isinstance(settings.BATCH_MULTI_VIDEO_ENABLE, bool)

    def test_test_mode_reduces_counts(self):
        """测试模式降低计数"""
        # 保存原始值
        original = settings.BATCH_PHASE1_COUNT

        # 启用测试模式
        settings.BATCH_TEST_MODE = True

        # 重新加载设置（模拟）
        if settings.BATCH_TEST_MODE:
            assert settings.BATCH_PHASE1_COUNT == 1
            assert settings.BATCH_PHASE2_COUNT == 1

        # 恢复
        settings.BATCH_TEST_MODE = False
        settings.BATCH_PHASE1_COUNT = original

    def test_score_threshold(self):
        """测试评分阈值配置"""
        assert hasattr(settings, "BATCH_SCORE_THRESHOLD")
        assert isinstance(settings.BATCH_SCORE_THRESHOLD, (int, float))
        assert 0 < settings.BATCH_SCORE_THRESHOLD <= 10


class TestEndToEnd:
    """端到端测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        self.test_output_dir = tempfile.mkdtemp()
        self.original_results_dir = settings.BATCH_RESULTS_DIR

        # 使用临时目录
        settings.BATCH_RESULTS_DIR = self.test_output_dir

        yield

        # 清理
        settings.BATCH_RESULTS_DIR = self.original_results_dir
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_summary_generation(self):
        """测试 summary 生成"""
        from batch_generator import scan_multi_video_sources

        videos = scan_videos(settings.DATA_DIR)
        if len(videos) < 2:
            pytest.skip("Need at least 2 videos")

        # 只验证数据结构，不运行完整流程
        sources = scan_multi_video_sources(settings.DATA_DIR)

        assert len(sources) >= 2
        for source in sources:
            assert "video_id" in source
            assert "video_path" in source
            assert "srt_path" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
