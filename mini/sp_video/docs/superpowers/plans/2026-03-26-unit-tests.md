# Unit Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 sp_video 项目的纯函数模块编写单元测试，覆盖 interval.py、time_utils.py、mode2.py 中的核心逻辑。

**Architecture:** 在 `tests/` 目录创建对应测试文件，使用 pytest 框架，测试不调用 LLM/ffmpeg，全部为纯函数测试。

**Tech Stack:** Python 3, pytest

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `tests/__init__.py` | 空文件，使 tests 成为包 |
| `tests/test_interval.py` | 测试 make_time/interval.py |
| `tests/test_time_utils.py` | 测试 make_time/time_utils.py |
| `tests/test_mode2_parse.py` | 测试 mode2.get_yuanwen_mode2() 的解析逻辑 |

工作目录：`/home/admin/claude/sp_v2/split_video/mini/sp_video`

---

### Task 1: 初始化测试目录

**Files:**
- Create: `tests/__init__.py`

- [ ] **Step 1: 创建空 `__init__.py`**

```bash
mkdir -p tests && touch tests/__init__.py
```

- [ ] **Step 2: 确认 pytest 可用**

```bash
cd /home/admin/claude/sp_v2/split_video/mini/sp_video && python -m pytest --version
```

期望输出：pytest 版本信息（若报错则 `pip install pytest`）

---

### Task 2: 测试 interval.py

**Files:**
- Create: `tests/test_interval.py`
- Reference: `make_time/interval.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_interval.py`：

```python
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
```

- [ ] **Step 2: 运行验证失败（模块存在时大部分应通过）**

```bash
cd /home/admin/claude/sp_v2/split_video/mini/sp_video && python -m pytest tests/test_interval.py -v
```

- [ ] **Step 3: 修复失败测试（如有）**

若测试失败，检查实际函数签名与期望是否一致，修正测试断言。

- [ ] **Step 4: 确认全部通过**

```bash
cd /home/admin/claude/sp_v2/split_video/mini/sp_video && python -m pytest tests/test_interval.py -v
```

期望：所有测试 PASSED

---

### Task 3: 测试 time_utils.py

**Files:**
- Create: `tests/test_time_utils.py`
- Reference: `make_time/time_utils.py`

- [ ] **Step 1: 写测试**

创建 `tests/test_time_utils.py`：

```python
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
```

- [ ] **Step 2: 运行测试**

```bash
cd /home/admin/claude/sp_v2/split_video/mini/sp_video && python -m pytest tests/test_time_utils.py -v
```

- [ ] **Step 3: 修复失败（如有），确认全部通过**

```bash
cd /home/admin/claude/sp_v2/split_video/mini/sp_video && python -m pytest tests/test_time_utils.py -v
```

期望：所有测试 PASSED

---

### Task 4: 测试 mode2.get_yuanwen_mode2()

**Files:**
- Create: `tests/test_mode2_parse.py`
- Reference: `make_time/mode2.py`

注意：`get_yuanwen_mode2` 只解析文本，不调用 AI，可直接测试。

- [ ] **Step 1: 写测试**

创建 `tests/test_mode2_parse.py`：

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from make_time.mode2 import get_yuanwen_mode2


# --- get_yuanwen_mode2 ---

SCRIPT_WITH_TIME = """\
观点：顺序颠倒导致战略失效（00:02:15-00:05:15）
00:02:15,000 --> 00:02:20,000
第一句字幕
00:02:20,000 --> 00:02:25,000
第二句字幕
解释：方法论（00:05:15-00:08:00）
00:05:15,000 --> 00:05:20,000
解释内容
"""

SCRIPT_WITHOUT_TIME = """\
观点：
00:02:15,000 --> 00:02:20,000
第一句字幕
解释：
00:05:15,000 --> 00:05:20,000
解释内容
"""


def test_parse_script_with_time_returns_parts():
    result = get_yuanwen_mode2(SCRIPT_WITH_TIME)
    # 应解析出至少2个 part（观点、解释）
    parts = [p for p in result if p['part_name'] != 'default']
    assert len(parts) >= 2

def test_parse_script_with_time_part_name():
    result = get_yuanwen_mode2(SCRIPT_WITH_TIME)
    names = [p['part_name'] for p in result]
    assert '观点' in names

def test_parse_script_with_time_has_zimu():
    result = get_yuanwen_mode2(SCRIPT_WITH_TIME)
    guan_dian = next(p for p in result if p['part_name'] == '观点')
    assert len(guan_dian['zimu_list']) >= 1

def test_parse_script_with_time_part_time():
    result = get_yuanwen_mode2(SCRIPT_WITH_TIME)
    guan_dian = next(p for p in result if p['part_name'] == '观点')
    assert guan_dian['part_time'] == ['00:02:15', '00:05:15']

def test_parse_script_without_time_label():
    result = get_yuanwen_mode2(SCRIPT_WITHOUT_TIME)
    names = [p['part_name'] for p in result]
    # 无时间标签的格式，part_name 含完整行（如 "观点："）
    assert any('观点' in n for n in names)

def test_parse_empty_script():
    result = get_yuanwen_mode2("")
    # 空脚本返回只含 default part 的列表
    assert isinstance(result, list)
```

- [ ] **Step 2: 运行测试**

```bash
cd /home/admin/claude/sp_v2/split_video/mini/sp_video && python -m pytest tests/test_mode2_parse.py -v
```

- [ ] **Step 3: 修复失败，确认全部通过**

```bash
cd /home/admin/claude/sp_v2/split_video/mini/sp_video && python -m pytest tests/test_mode2_parse.py -v
```

---

### Task 5: 整体运行 + 汇总

- [ ] **Step 1: 运行所有测试**

```bash
cd /home/admin/claude/sp_v2/split_video/mini/sp_video && python -m pytest tests/ -v --tb=short
```

- [ ] **Step 2: 确认通过率**

期望：所有测试 PASSED（或记录已知跳过/失败原因）

- [ ] **Step 3: 汇报结果**

输出测试汇总（通过/失败数量），如有失败列出具体原因。

---

## 范围说明

**不在本次计划内：**
- AI 匹配逻辑（ai_caller.py）—— 需要 mock LLM，复杂度高，单独计划
- ffmpeg 相关（step3.py）—— 需要真实视频文件
- skill.py / main.py —— 集成测试，不在此次范围
