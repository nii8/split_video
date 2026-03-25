import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from make_time.time_utils import (
    set_yuan_line,
    remove_milliseconds,
    is_start_bigger_end,
    check_timeline_format,
    get_zimu_index_list_by_time,
)


# --- set_yuan_line ---
def test_set_yuan_line_removes_quotes():
    assert set_yuan_line('"hello"') == "hello"

def test_set_yuan_line_removes_chinese_quotes():
    assert set_yuan_line('\u201chello\u201d') == "hello"

def test_set_yuan_line_no_quotes():
    assert set_yuan_line("hello") == "hello"

def test_set_yuan_line_strips_spaces():
    assert set_yuan_line("  hello  ") == "hello"


# --- remove_milliseconds ---
def test_remove_milliseconds_basic():
    result = remove_milliseconds(["00:00:01,733 ", " 00:00:02,300"])
    assert result == ["00:00:01", "00:00:02"]

def test_remove_milliseconds_single():
    assert remove_milliseconds(["00:01:23,456"]) == ["00:01:23"]


# --- is_start_bigger_end ---
def test_is_start_bigger_end_equal():
    assert is_start_bigger_end("00:00:05,000", "00:00:05,000") is True

def test_is_start_bigger_end_true():
    assert is_start_bigger_end("00:00:06,000", "00:00:05,000") is True

def test_is_start_bigger_end_false():
    assert is_start_bigger_end("00:00:04,000", "00:00:05,000") is False

def test_is_start_bigger_end_no_milliseconds():
    assert is_start_bigger_end("00:01:00", "00:00:59") is True


# --- check_timeline_format ---
def test_check_timeline_format_valid():
    ok, parts = check_timeline_format("00:00:01,000 --> 00:00:02,500")
    assert ok is True
    assert parts == ["00:00:01,000", "00:00:02,500"]

def test_check_timeline_format_invalid():
    ok, parts = check_timeline_format("this is not a timeline")
    assert ok is False
    assert parts == [None, None]

def test_check_timeline_format_partial():
    ok, _ = check_timeline_format("00:00:01,000 ->  00:00:02,500")
    assert ok is False


# --- get_zimu_index_list_by_time ---
def _make_zimu_list(entries):
    """entries = (id, start, end, text)"""
    return [(e[0], [e[1], e[2]], e[3]) for e in entries]

def test_get_zimu_index_list_by_time_found():
    zimu_list = _make_zimu_list([
        (1, "00:00:01,000", "00:00:02,000", "hello world"),
        (2, "00:00:02,000", "00:00:03,000", "foo bar"),
        (3, "00:00:03,000", "00:00:04,000", "baz qux"),
        (4, "00:00:04,000", "00:00:05,000", "test"),
        (5, "00:00:05,000", "00:00:06,000", "end"),
    ])
    yuan = {"text": "hello", "time": "00:00:00"}
    result = get_zimu_index_list_by_time(zimu_list, yuan)
    # 应返回包含周边字幕的子列表
    assert isinstance(result, list)

def test_get_zimu_index_list_by_time_empty_when_time_exceeds():
    zimu_list = _make_zimu_list([
        (1, "00:00:01,000", "00:00:02,000", "hello"),
    ])
    # 参考时间超过所有字幕
    yuan = {"text": "hello", "time": "00:01:00"}
    result = get_zimu_index_list_by_time(zimu_list, yuan)
    assert result == []