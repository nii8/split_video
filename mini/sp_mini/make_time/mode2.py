import re

import settings
from batch.output import debug, warn

from .time_utils import check_timeline_format, set_yuan_line, get_zimu_index_list_by_time
from .interval import merge_intervals, get_start_end_t_id_list
from .ai_caller import call_ai_match, find_intervals_by_ai, save_result_to_json
from .prompts import build_match_subtitle_prompt

glo_ask_modal_name = 'qwen'
glo_part_list = ["观点：", "解释：", "故事：", "出路："]


def get_yuanwen_mode2(wenan_content):
    yuanwen_list = []
    current_part = {
        'part_name': 'default',
        'part_text': 'default',
        'part_time': [1, 1],
        'zimu_list': []
    }

    for line in wenan_content.split('\n'):
        line = line.strip()
        if not line:
            continue

        part_match = re.match(r'^(.+)：(.+)（(\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2})）$', line)
        if part_match:
            if current_part:
                yuanwen_list.append(current_part)

            current_part = {
                'part_name': part_match.group(1),
                'part_text': part_match.group(2),
                'part_time': [part_match.group(3), part_match.group(4)],
                'zimu_list': []
            }
            continue

        count_part = 0
        for part in glo_part_list:
            if part in line:
                count_part += 1
        if count_part >= 1:
            if current_part:
                yuanwen_list.append(current_part)
            current_part = {
                'part_name': line,
                'part_text': line,
                'part_time': [1, 1],
                'zimu_list': []
            }
            debug(f'part line={line} count_part={count_part}')
            continue

        ret, (start_t, end_t) = check_timeline_format(line)
        if ret:
            current_zimu = {
                'time_text': line,
                'start': start_t,
                'end': end_t,
                'text': None
            }
            if 'zimu_list' in current_part:
                current_part['zimu_list'].append(current_zimu)
            else:
                warn(f'zimu_list not in current_part line={line} current_part={current_part}')
            continue

        if current_part and current_part['zimu_list']:
            last_zimu = current_part['zimu_list'][-1]
            if last_zimu['text'] is None:
                if '...' in line:
                    yuan_text1 = line.split('...')[0]
                    yuan_text2 = line.split('...')[1]
                    last_zimu['text'] = yuan_text1
                    new_zimu = {
                        'time_text': last_zimu['time_text'],
                        'start': last_zimu['start'],
                        'end': last_zimu['end'],
                        'text': yuan_text2
                    }
                    current_part['zimu_list'].append(new_zimu)
                elif '……' in line:
                    yuan_text1 = line.split('……')[0]
                    yuan_text2 = line.split('……')[1]
                    last_zimu['text'] = yuan_text1
                    new_zimu = {
                        'time_text': last_zimu['time_text'],
                        'start': last_zimu['start'],
                        'end': last_zimu['end'],
                        'text': yuan_text2
                    }
                    current_part['zimu_list'].append(new_zimu)
                else:
                    last_zimu['text'] = line
            else:
                last_zimu['text'] = f"{last_zimu['text']} {line}".strip()
            continue

        debug(f'other line={line}')

    if current_part:
        yuanwen_list.append(current_part)

    return yuanwen_list


def get_srt_list_by_time(zimu_list, start, end, yuan_text):
    yuan_wen_list = [
        {"text": yuan_text, "time": start},
        {"text": yuan_text, "time": end}
    ]
    debug(f'mod = 2 yuan_wen_list={yuan_wen_list}')
    yuan_wen_srt_list = []
    for yuan in yuan_wen_list:
        mini_zimu_list = get_zimu_index_list_by_time(zimu_list, yuan)
        yuan_wen_srt_list.append([yuan, mini_zimu_list])
    return yuan_wen_srt_list


def _collect_keeps(ask, zimu, yuan_text, keep_intervals):
    unit_intervals = call_ai_match(ask, zimu, yuan_text, glo_ask_modal_name)
    for unit_start, unit_end, unit_id_list, unit_zimu in unit_intervals:
        if unit_start:
            keep_intervals.append([unit_start, unit_end, unit_id_list, unit_zimu])
            continue
        id_list = find_intervals_by_ai(yuan_text, zimu, glo_ask_modal_name)
        if id_list:
            unit = get_start_end_t_id_list(zimu, id_list)
            if unit[0]:
                keep_intervals.append(unit)
                continue
        keep_intervals.append([None, None, None, unit_zimu])
    return keep_intervals


def get_intervals_by_ai_mode2(yuan_wen_srt_list):
    keep_intervals = []
    for yuan, zimu in yuan_wen_srt_list:
        yuan_text = yuan['text'] + ' (' + yuan['time'] + ')'
        zimu_union_text = ''.join(
            f'{zid}\n{s} --> {e}\n{txt}\n\n\n'
            for zid, (s, e), txt in zimu
        )
        yuan_text1 = yuan_text2 = None
        for sep in ('...', '……'):
            if sep in yuan_text:
                parts = yuan['text'].split(sep)
                suffix = ' (' + yuan['time'] + ')'
                yuan_text1 = parts[0] + suffix
                yuan_text2 = parts[1] + suffix
                break
        if yuan_text1:
            keep_intervals = _collect_keeps(build_match_subtitle_prompt(yuan_text1, zimu_union_text), zimu, yuan_text1, keep_intervals)
            keep_intervals = _collect_keeps(build_match_subtitle_prompt(yuan_text2, zimu_union_text), zimu, yuan_text2, keep_intervals)
        else:
            keep_intervals = _collect_keeps(build_match_subtitle_prompt(yuan_text, zimu_union_text), zimu, yuan_text, keep_intervals)

    debug(f'AI keep_intervals={keep_intervals}')
    return keep_intervals


def get_zimu_from_start_end(zimu_list, start, end, yuan_text):
    for zimu_id, (start_t, end_t), zimu_str in zimu_list:
        if start == start_t and end == end_t and yuan_text == zimu_str:
            return start_t, end_t, zimu_id, zimu_str, 0
    for zimu_id, (start_t, end_t), zimu_str in zimu_list:
        if start == end_t and yuan_text == zimu_str:
            return start_t, end_t, zimu_id, zimu_str, 1
        if end == start_t and yuan_text == zimu_str:
            return start_t, end_t, zimu_id, zimu_str, 1
    for zimu_id, (start_t, end_t), zimu_str in zimu_list:
        if yuan_text == zimu_str:
            start = start_t
            end = end_t
            break
    yuan_wen_srt_list = get_srt_list_by_time(zimu_list, start, end, yuan_text)
    for srt_list in yuan_wen_srt_list:
        keep_intervals = get_intervals_by_ai_mode2([srt_list])
        interval = keep_intervals[0]
        if interval[0]:
            return interval[0], interval[1], interval[2], interval[3], 2
    return None, None, None, None, None


def get_intervals_by_yuanwen(yuanwen, zimu_list):
    intervals = []
    for part in yuanwen:
        for yuan in part['zimu_list']:
            start = yuan['start']
            end = yuan['end']
            yuan_text = set_yuan_line(yuan['text'])
            start, end, id_list, zimu_str, zimu_mode = get_zimu_from_start_end(zimu_list, start, end, yuan_text)
            if start:
                intervals.append([start, end, id_list, zimu_str, zimu_mode])
            else:
                warn(f'interval match error: {yuan}')
                intervals.append([None, None, None, yuan_text, 0])
    keep_intervals, merged_list = merge_intervals(zimu_list, intervals)
    debug('merge_keep_intervals=')
    for keep in keep_intervals:
        debug(str(keep))
    debug(f'merged_list={merged_list}')
    result = {'keep_intervals': keep_intervals, 'merged_intervals': merged_list}
    save_result_to_json(result)
    return result


def get_intervals_by_mode2(wenan_content, zimu_list):
    yuanwen = get_yuanwen_mode2(wenan_content)
    result = get_intervals_by_yuanwen(yuanwen, zimu_list)
    return result
