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