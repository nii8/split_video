import pytest
from batch.evaluator import evaluate_quality


def test_evaluate_quality_basic():
    """测试基本评分功能"""
    intervals = [
        [("00:00:10,000", "00:00:20,000"), "测试文本1"],
        [("00:00:30,000", "00:00:40,000"), "测试文本2"],
        [("00:00:50,000", "00:01:00,000"), "测试文本3"],
    ]
    score = evaluate_quality("dummy.mp4", intervals)
    assert "video" in score
    assert "transition" in score
    assert "audio" in score
    assert "total" in score
    assert 0 <= score["total"] <= 10


def test_evaluate_quality_range():
    """测试评分范围"""
    intervals = [[("00:00:10,000", "00:00:20,000"), "测试"]]
    score = evaluate_quality("dummy.mp4", intervals)
    assert 0 <= score["video"] <= 4
    assert 0 <= score["transition"] <= 3
    assert 0 <= score["audio"] <= 3


def test_evaluate_quality_empty():
    """测试空 intervals"""
    score = evaluate_quality("dummy.mp4", [])
    assert score["total"] >= 0
