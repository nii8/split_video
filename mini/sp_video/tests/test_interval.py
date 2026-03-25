import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from make_time.interval import (
    is_consecutive,
    group_consecutive_ids,
    get_start_end_t_id_list,
    merge_intervals,
)


# --- is_consecutive ---
def test_is_consecutive_true():
    assert is_consecutive([1, 2, 3]) is True

def test_is_consecutive_false():
    assert is_consecutive([1, 3]) is False

def test_is_consecutive_single():
    assert is_consecutive([5]) is True

def test_is_consecutive_empty():
    assert is_consecutive([]) is True


# --- group_consecutive_ids ---
def test_group_consecutive_ids_basic():
    assert group_consecutive_ids([1, 2, 4, 5, 6]) == [[1, 2], [4, 5, 6]]

def test_group_consecutive_ids_all_separate():
    assert group_consecutive_ids([1, 3, 5]) == [[1], [3], [5]]

def test_group_consecutive_ids_empty():
    assert group_consecutive_ids([]) == []

def test_group_consecutive_ids_single():
    assert group_consecutive_ids([7]) == [[7]]


# --- get_start_end_t_id_list ---
def _make_zimu(*entries):
    """Helper: entries = (id, start, end, text)"""
    return [(e[0], [e[1], e[2]], e[3]) for e in entries]

def test_get_start_end_t_id_list_found():
    zimu = _make_zimu(
        (1, "00:00:01,000", "00:00:02,000", "hello"),
        (2, "00:00:02,000", "00:00:03,000", "world"),
        (3, "00:00:03,000", "00:00:04,000", "foo"),
    )
    result = get_start_end_t_id_list(zimu, [1, 2])
    assert result[0] == "00:00:01,000"
    assert result[1] == "00:00:03,000"
    assert result[2] == [1, 2]

def test_get_start_end_t_id_list_not_found():
    zimu = _make_zimu(
        (1, "00:00:01,000", "00:00:02,000", "hello"),
    )
    result = get_start_end_t_id_list(zimu, [99])
    assert result == [None, None, None, None]


# --- merge_intervals ---
def test_merge_intervals_consecutive():
    filter_zimu = [
        (1, ["00:00:01,000", "00:00:02,000"], "A"),
        (2, ["00:00:02,000", "00:00:03,000"], "B"),
        (3, ["00:00:03,000", "00:00:04,000"], "C"),
    ]
    keep = [
        ("00:00:01,000", "00:00:02,000", [1], "text1", None),
        ("00:00:02,000", "00:00:03,000", [2], "text2", None),
    ]
    merged, merged_list = merge_intervals(filter_zimu, keep)
    # 连续区间应合并为一段
    assert len(merged) == 1
    assert merged[0][0] == ["00:00:01,000", "00:00:03,000"]

def test_merge_intervals_non_consecutive():
    filter_zimu = [
        (1, ["00:00:01,000", "00:00:02,000"], "A"),
        (3, ["00:00:05,000", "00:00:06,000"], "C"),
    ]
    keep = [
        ("00:00:01,000", "00:00:02,000", [1], "text1", None),
        ("00:00:05,000", "00:00:06,000", [3], "text2", None),
    ]
    merged, merged_list = merge_intervals(filter_zimu, keep)
    # 不连续，保持两段
    assert len(merged) == 2

def test_merge_intervals_with_none():
    """含 None 时间的区间不合并"""
    filter_zimu = [(1, ["00:00:01,000", "00:00:02,000"], "A")]
    keep = [
        (None, None, [], "unmatched", None),
    ]
    merged, _ = merge_intervals(filter_zimu, keep)
    assert merged[0][0] == [None, None]