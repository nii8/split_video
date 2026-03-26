import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from make_video.step3 import (
    extract_keyframes,
    find_nearest_keyframe_before,
    probe_video_duration,
)


class TestFindNearestKeyframeBefore:
    """二分查找测试"""

    def test_normal_case(self):
        keyframes = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert find_nearest_keyframe_before(keyframes, 2.5) == 2.0
        assert find_nearest_keyframe_before(keyframes, 3.0) == 3.0
        assert find_nearest_keyframe_before(keyframes, 4.1) == 4.0

    def test_exact_match(self):
        keyframes = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert find_nearest_keyframe_before(keyframes, 3.0) == 3.0

    def test_before_first(self):
        keyframes = [1.0, 2.0, 3.0]
        assert find_nearest_keyframe_before(keyframes, 0.5) is None

    def test_empty_list(self):
        assert find_nearest_keyframe_before([], 2.0) is None

    def test_exceeds_range(self):
        keyframes = [1.0, 2.0, 3.0]
        assert find_nearest_keyframe_before(keyframes, 100.0) == 3.0

    def test_at_first_keyframe(self):
        keyframes = [1.0, 2.0, 3.0]
        assert find_nearest_keyframe_before(keyframes, 1.0) == 1.0


class TestExtractKeyframes:
    """关键帧提取测试"""

    def test_file_not_exists(self):
        result = extract_keyframes("/nonexistent/video.mp4")
        assert result == []

    def test_invalid_file(self):
        result = extract_keyframes("/tmp/not_a_video.txt")
        assert result == []

    def test_with_real_video(self):
        video_path = "/home/admin/claude/sp_v2/split_video/mini/sp_video/data/hanbing/C1873/C1873.mp4"
        if not os.path.exists(video_path):
            pytest.skip("Real video not available")

        result = extract_keyframes(video_path)
        assert isinstance(result, list)


class TestProbeVideoDuration:
    """时长测量测试"""

    def test_file_not_exists(self):
        result = probe_video_duration("/nonexistent/video.mp4")
        assert result is None

    def test_invalid_file(self):
        result = probe_video_duration("/tmp/not_a_video.txt")
        assert result is None

    def test_with_sample_video(self):
        import subprocess

        result = subprocess.run(
            [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "testsrc=d=5:size=320x240",
                "-c:v",
                "libx264",
                "-y",
                "/tmp/test_duration.mp4",
            ],
            capture_output=True,
            timeout=30,
        )
        assert result.returncode == 0, "Failed to create test video"

        duration = probe_video_duration("/tmp/test_duration.mp4")
        assert duration is not None
        assert isinstance(duration, float)
        assert 4.5 < duration < 5.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
