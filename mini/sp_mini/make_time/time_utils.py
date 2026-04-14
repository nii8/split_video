"""
make_time/time_utils.py — 时间字符串处理 + 字幕时间区间查找
"""
import re
from datetime import datetime


def set_yuan_line(line):
    """去掉首尾中文引号。"""
    line = line.strip()
    if line.startswith(('"', '\u201c')):
        line = line[1:]
    line = line.strip()
    if line.endswith(('"', '\u201d')):
        line = line[:-1]
    return line


def remove_milliseconds(time_list):
    """['00:00:01,733 ', ' 00:00:02,300'] → ['00:00:01', '00:00:02']"""
    return [t.strip().split(',')[0] for t in time_list]


def is_start_bigger_end(start: str, end: str) -> bool:
    """判断 start >= end（支持 HH:MM:SS 和 HH:MM:SS,fff/HH:MM:SS.fff 格式）。"""
    start_c = start.replace(',', '.')
    end_c   = end.replace(',', '.')
    fmt_s   = "%H:%M:%S.%f" if '.' in start_c else "%H:%M:%S"
    fmt_e   = "%H:%M:%S.%f" if '.' in end_c   else "%H:%M:%S"
    return datetime.strptime(start_c, fmt_s) >= datetime.strptime(end_c, fmt_e)


def check_timeline_format(line):
    """
    检查是否是 SRT 时间轴行（'00:00:01,000 --> 00:00:02,000'）。
    返回 (True, [start, end]) 或 (False, [None, None])。
    """
    pattern = r'^(\d{2}:\d{2}:\d{2},\d{3})\s-->\s(\d{2}:\d{2}:\d{2},\d{3})$'
    m = re.fullmatch(pattern, line.strip())
    if m:
        return True, [m.group(1), m.group(2)]
    return False, [None, None]


def get_zimu_index_list_by_time(zimu_list, yuan):
    """
    给定文案条目（含参考时间），从 zimu_list 中找出附近的候选字幕窗口。
    返回候选字幕子列表。
    """
    yuan_text = yuan["text"]
    yuan_time = yuan["time"]
    yuan_len  = len(yuan_text)

    ok_index = start_index = end_index = None

    for index, zimu in enumerate(zimu_list):
        zimu_t = remove_milliseconds(zimu[1])
        start_time, _ = zimu_t
        if is_start_bigger_end(start_time, yuan_time):
            ok_index = zimu[0]
            # 向前找 start_index
            cp_len = 0
            for i in range(20):
                if index - i - 1 > 0:
                    child  = zimu_list[index - i - 1]
                    cp_len += len(child[2])
                    if cp_len > yuan_len * 2 and i > 10:
                        start_index = child[0]
                        break
            if not start_index:
                start_index = max(1, ok_index - 5)
            # 向后找 end_index
            cp_len = 0
            for i in range(20):
                if index + i < len(zimu_list) - 1:
                    child  = zimu_list[index + i]
                    cp_len += len(child[2])
                    if cp_len > yuan_len * 2 and i > 10:
                        end_index = child[0]
                        break
            if not end_index:
                end_index = min(len(zimu_list), ok_index + 5)
            break

    if start_index is None or end_index is None:
        return []
    return [z for z in zimu_list if start_index <= z[0] <= end_index]

