import pytest
from make_video.filter_builder import build_filter_complex
from make_video.step3 import srt_time_to_seconds


def test_build_filter_complex_single_segment():
    """Test build_filter_complex with a single segment"""
    segments = [(10.0, 20.0)]
    expected = (
        "[0:v]trim=start=10.0:end=20.0,setpts=PTS-STARTPTS[v0];"
        "[0:a]atrim=start=10.0:end=20.0,asetpts=PTS-STARTPTS[a0];"
        "[v0][a0]concat=n=1:v=1:a=1[outv][outa]"
    )
    result = build_filter_complex(segments)
    assert result == expected


def test_build_filter_complex_multiple_segments():
    """Test build_filter_complex with multiple segments"""
    segments = [(10.0, 20.0), (30.5, 40.3)]
    expected = (
        "[0:v]trim=start=10.0:end=20.0,setpts=PTS-STARTPTS[v0];"
        "[0:a]atrim=start=10.0:end=20.0,asetpts=PTS-STARTPTS[a0];"
        "[0:v]trim=start=30.5:end=40.3,setpts=PTS-STARTPTS[v1];"
        "[0:a]atrim=start=30.5:end=40.3,asetpts=PTS-STARTPTS[a1];"
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
    )
    result = build_filter_complex(segments)
    assert result == expected


def test_build_filter_complex_empty_list():
    """Test build_filter_complex with empty list raises ValueError"""
    with pytest.raises(ValueError) as excinfo:
        build_filter_complex([])
    assert "Segments list cannot be empty" in str(excinfo.value)


def test_build_filter_complex_with_correct_syntax():
    """Test that build_filter_complex generates correct syntax containing needed components"""
    segments = [(5.0, 15.0), (25.0, 35.0)]
    result = build_filter_complex(segments)

    # Verify the result contains the required components
    assert "trim=" in result
    assert "atrim=" in result
    assert "setpts=" in result
    assert "asetpts=" in result
    assert "concat=" in result
    assert "[outv]" in result
    assert "[outa]" in result


def test_srt_time_to_seconds_standard_format():
    """Test srt_time_to_seconds with standard format"""
    result = srt_time_to_seconds("00:01:23,456")
    assert result == 83.456


def test_srt_time_to_seconds_zero_time():
    """Test srt_time_to_seconds with zero time format"""
    result = srt_time_to_seconds("00:00:10,000")
    assert result == 10.0


def test_srt_time_to_seconds_hour_format():
    """Test srt_time_to_seconds with hour format"""
    result = srt_time_to_seconds("01:00:00,000")
    assert result == 3600.0


def test_srt_time_to_seconds_fraction_precision():
    """Test srt_time_to_seconds preserves fractional second precision"""
    result = srt_time_to_seconds("00:00:00,789")
    assert result == 0.789
