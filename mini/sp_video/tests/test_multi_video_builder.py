import os
import tempfile

import pytest

from make_video.multi_video_builder import (
    build_multi_video_command,
    build_multi_video_filter_complex,
)


def test_build_multi_video_filter_complex_skips_invalid_segments():
    sources = [{"video_id": "A", "video_path": "/tmp/A.mp4"}]
    segments = [
        {"video_id": "A", "start": 0, "end": 5, "text": "ok"},
        {"video_id": "A", "start": 3, "end": 3, "text": "bad"},
        {"video_id": "A", "start": None, "end": 7, "text": "bad"},
    ]

    result = build_multi_video_filter_complex(sources, segments)
    assert "trim=start=0:end=5" in result
    assert "concat=n=1:v=1:a=1[outv][outa]" in result


def test_build_multi_video_filter_complex_no_valid_segments_raises():
    sources = [{"video_id": "A", "video_path": "/tmp/A.mp4"}]
    segments = [{"video_id": "A", "start": 5, "end": 5, "text": "bad"}]

    with pytest.raises(ValueError) as excinfo:
        build_multi_video_filter_complex(sources, segments)

    assert "No valid segments found" in str(excinfo.value)


def test_build_multi_video_command_uses_unique_input_paths():
    with tempfile.TemporaryDirectory() as temp_dir:
        path_a = os.path.join(temp_dir, "A.mp4")
        path_b = os.path.join(temp_dir, "B.mp4")
        open(path_a, "a").close()
        open(path_b, "a").close()

        sources = [
            {"video_id": "A", "video_path": path_a},
            {"video_id": "B", "video_path": path_b},
        ]
        segments = [
            {"video_id": "A", "start": 0, "end": 5, "text": "a1"},
            {"video_id": "B", "start": 1, "end": 4, "text": "b1"},
            {"video_id": "A", "start": 6, "end": 8, "text": "a2"},
        ]

        cmd, input_paths = build_multi_video_command(
            sources,
            segments,
            os.path.join(temp_dir, "out.mp4"),
        )

        assert input_paths == [path_a, path_b]
        assert cmd.count("-i") == 2
