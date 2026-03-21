"""
make_time/interval.py — 时间区间分组、合并
"""


def is_consecutive(lst):
    """检查整数列表是否连续（有序）。"""
    if len(lst) <= 1:
        return True
    s = sorted(lst)
    return s == list(range(s[0], s[-1] + 1))


def group_consecutive_ids(id_list):
    """
    将连续 ID 分组，保持原始顺序。
    例：[3,1,2,7] → [[3],[1,2],[7]]
    """
    if not id_list:
        return []
    result  = []
    current = [id_list[0]]
    for i in range(1, len(id_list)):
        if id_list[i] == id_list[i - 1] + 1:
            current.append(id_list[i])
        else:
            result.append(current)
            current = [id_list[i]]
    result.append(current)
    return result


def get_start_end_t_id_list(zimu, id_list):
    """
    从 zimu_list 中按 id_list 取出首尾时间戳和拼接文本。
    返回 [start_t, end_t, id_list, unit_zimu] 或 [None, None, None, None]。
    """
    start_t = end_t = None
    unit_zimu = ''
    for zimu_id, (start, end), zimu_str in zimu:
        if zimu_id == id_list[0]:
            start_t = start
        if zimu_id == id_list[-1]:
            end_t = end
        if zimu_id in id_list:
            unit_zimu = unit_zimu + ' ' + zimu_str
    if start_t and end_t:
        return [start_t, end_t, id_list, unit_zimu]
    print(f'get_start_end_t_id_list error: start={start_t}, end={end_t}')
    return [None, None, None, None]


def merge_intervals(filter_zimu_list, keep_intervals):
    """
    将相邻（字幕 ID 连续）的区间自动合并为一段。

    filter_zimu_list: [num, [start, end], text]
    keep_intervals:   [start_t, end_t, id_list, yuan_text, zimu_mode]
    返回: (merged, merged_list)
      merged      = [[[start, end], text], ...]
      merged_list = [[start, end], ...]
    """
    num_to_time = {item[0]: (item[1][0], item[1][1]) for item in filter_zimu_list}

    merged = []
    merged_list = []
    i = 0
    n = len(keep_intervals)

    while i < n:
        cur_start, cur_end, cur_ids, cur_text, cur_mode = keep_intervals[i]
        if cur_mode:
            cur_text += f'[[mode={cur_mode}]]'
        j = i + 1

        if cur_start and cur_end:
            while j < n:
                nxt_start, nxt_end, _, nxt_text, nxt_mode = keep_intervals[j]
                cur_num = next((n for n, (_, e) in num_to_time.items() if e.strip() == cur_end), None)
                nxt_num = next((n for n, (s, _) in num_to_time.items() if s.strip() == nxt_start), None)
                if cur_num is not None and nxt_num is not None and nxt_num == cur_num + 1:
                    cur_end = nxt_end
                    if nxt_mode:
                        nxt_text += f'[[mode={nxt_mode}]]'
                    cur_text = cur_text + ' ' + nxt_text
                    j += 1
                else:
                    break

        merged.append([[cur_start, cur_end], cur_text])
        merged_list.append([cur_start, cur_end])
        i = j

    return merged, merged_list
