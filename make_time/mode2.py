import re
from .util import check_timeline_format, set_yuan_line, get_zimu_index_list_by_time, get_ai_json, get_check_promot
from .util import get_unit_interval_by_ai, merge_intervals, save_dict_to_json
from .util import get_intervals_by_ai_find, get_start_end_t_id_list

mode2_dic = {}
glo_ask_modal_name = 'deepseek'
glo_check_probability = 0.88
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

        # 检查是否是新的部分标题行
        # 观点解释：顺序颠倒导致战略失效（00:02:15-00:05:15）
        part_match = re.match(r'^(.+)：(.+)（(\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2})）$', line)
        if part_match:
            if current_part:  # 保存上一个part
                yuanwen_list.append(current_part)

            current_part = {
                'part_name': part_match.group(1),
                'part_text': part_match.group(2),
                'part_time': [part_match.group(3), part_match.group(4)],
                'zimu_list': []
            }
            continue
        else:
            count_part = 0
            for part in glo_part_list:
                if part in line:
                    count_part += 1
            if count_part >= 1:
                if current_part:  # 保存上一个part
                    yuanwen_list.append(current_part)
                current_part = {
                    'part_name': line,
                    'part_text': line,
                    'part_time': [1, 1],
                    'zimu_list': []
                }
                print(f'===line={line} count_part={count_part}')
                continue

        # 检查是否是时间轴行
        ret, (start_t, end_t) = check_timeline_format(line)
        if ret:
            current_zimu = {
                'time_text': line,
                'start': start_t,
                'end': end_t,
                'text': None  # 下一行是文本
            }
            if 'zimu_list' in current_part:
                current_part['zimu_list'].append(current_zimu)
            else:
                print(f'error:zimu_list not in current_part line={line} current_part={current_part}')
            continue

        # 如果是文本行且当前有字幕条目
        if current_part and current_part['zimu_list'] and current_part['zimu_list'][-1]['text'] is None:
            if '...' in line:
                yuan_text1 = line.split('...')[0]
                yuan_text2 = line.split('...')[1]
                current_part['zimu_list'][-1]['text'] = yuan_text1
                new_zimu = {
                    'time_text': current_part['zimu_list'][-1]['time_text'],
                    'start': current_part['zimu_list'][-1]['start'],
                    'end': current_part['zimu_list'][-1]['end'],
                    'text': yuan_text2  
                }
                current_part['zimu_list'].append(new_zimu)
            elif '……' in line:
                yuan_text1 = line.split('……')[0]
                yuan_text2 = line.split('……')[1]
                current_part['zimu_list'][-1]['text'] = yuan_text1
                new_zimu = {
                    'time_text': current_part['zimu_list'][-1]['time_text'],
                    'start': current_part['zimu_list'][-1]['start'],
                    'end': current_part['zimu_list'][-1]['end'],
                    'text': yuan_text2
                }
                current_part['zimu_list'].append(new_zimu)
            else:
                current_part['zimu_list'][-1]['text'] = line
            continue
        print(f'other: line={line}')

    # 添加最后一个part
    if current_part:
        yuanwen_list.append(current_part)

    return yuanwen_list



def get_srt_list_by_time(zimu_list, start, end, yuan_text):
    yuan_wen_list = [
        {"text": yuan_text, "time": start},
        {"text": yuan_text, "time": end}
    ]
    print(f'mod = 2 yuan_wen_list={yuan_wen_list}')
    yuan_wen_srt_list = []
    for yuan in yuan_wen_list:
        mini_zimu_list = get_zimu_index_list_by_time(zimu_list, yuan)
        yuan_wen_srt_list.append([yuan, mini_zimu_list])
    return yuan_wen_srt_list


def get_id_list_promot_mode2(yuan_text, zimu_union_text):

    example = f'''
[原文句子]
西方用SWOT分析 (00:03:40,100)

[时间序列]
104
00:03:25,100 --> 00:03:27,833
真正的你要知道敌人是什么


105
00:03:28,133 --> 00:03:29,866
你才有你的SWOT


106
00:03:30,233 --> 00:03:30,466
老师


107
00:03:30,466 --> 00:03:32,333
你可以给我们展开讲一下


108
00:03:32,433 --> 00:03:34,066
为什么西方用这个SWOT


109
00:03:34,066 --> 00:03:35,200
它到底解决什么问题

[正确输出]
{{
    "id_list": [108],
    "text": "为什么西方用这个SWOT"
}}

# 示例输入2：
'''

    ask = f'''请根据以下规则整理出与原文句子相关的时间序列并生成结构化JSON数据：
# 处理规则
1. 输入数据：
   - [时间序列]：字幕片段（含字幕id,时间戳和文本）
   - [原文句子]：需要匹配的目标句子（含参考时间点）

2. 匹配要求：
   - 将[时间序列]中与[原文句子]语义匹配的连续片段合并为一个条目
   - 合并的这个条目和原文句子精确匹配

3. JSON格式规范：
   - 条目包含：
     * id_list: 和原文句子匹配的字幕的id列表（数量和顺序与下面的文本text对应）
     * text: 合并后的完整文本（用空格连接片段）
{example}
# 示例输入：

[原文句子]
因为在上市公司我做事做得很好，我在那都是做的最好的，但是那个时候会觉得这好像都是自己的能力，其实有很多是平台的能力 (00:08:07)

[时间序列]
276
00:08:02,233 --> 00:08:04,866
就是错把平台的能力

277
00:08:04,866 --> 00:08:05,700
当自己的能力

278
00:08:06,233 --> 00:08:07,500
因为在上市公司我

279
00:08:07,500 --> 00:08:08,700
我做事做得很好

280
00:08:08,700 --> 00:08:10,400
我在那都是做的最好的

281
00:08:10,700 --> 00:08:12,833
但是这个呃

282
00:08:12,833 --> 00:08:13,666
那时候会觉得

283
00:08:13,666 --> 00:08:14,700
这好像都是自己的能力

284
00:08:14,700 --> 00:08:16,200
其实有很多是平台的能力

285
00:08:17,000 --> 00:08:18,200
资金不用你管

286
00:08:18,666 --> 00:08:21,100
那个研发的那帮人不用你管

287
00:08:21,100 --> 00:08:22,066
公司都给你弄好了

[正确输出]
{{
    "id_list": [278, 279, 280, 281, 282, 283, 284],
    "text": "因为在上市公司我 我做事做得很好 我在那都是做的最好的 但是这个呃 那时候会觉得 这好像都是自己的能力 其实有很多是平台的能力"
}}

# 待处理数据
[原文句子]
{yuan_text}

[时间序列]
{zimu_union_text}

请严格按照示例格式输出JSON，确保：
1. id_list, 合并的text 和 原文句子是匹配的
2. 文本内容用单个空格连接片段
3. 不使用换行符或特殊分隔符'''
    return ask


def get_keeps_mode2(ask, zimu, yuan_text, keep_intervals):
    unit_intervals = get_unit_interval_by_ai(ask, zimu, yuan_text, glo_ask_modal_name, glo_check_probability)
    for unit_start, unit_end, unit_id_list, unit_zimu in unit_intervals:
        if unit_start:
            keep_intervals.append([unit_start, unit_end, unit_id_list, unit_zimu])
            continue
        id_list = get_intervals_by_ai_find(yuan_text, zimu, glo_ask_modal_name)
        if id_list:
            unit = get_start_end_t_id_list(zimu, id_list)
            if unit[0]:
                keep_intervals.append(unit)
                continue
        keep_intervals.append([None, None, None, unit_zimu])
    return keep_intervals


def get_intervals_by_ai_mode2(yuan_wen_srt_list):
    keep_intervals = []
    for i, (yuan, zimu) in enumerate(yuan_wen_srt_list):
        yuan_text = yuan['text'] + ' (' + yuan['time'] + ')'
        zimu_union_text = ''
        for zimu_id, (start, end) , zimu_str, in zimu:
            zimu_union_text = zimu_union_text + f'{zimu_id}\n{start} --> {end}\n{zimu_str}\n\n\n'
        yuan_text1, yuan_text2 = None, None
        if '...' in yuan_text:
            yuan_text1 = yuan['text'].split('...')[0] + ' (' + yuan['time'] + ')'
            yuan_text2 = yuan['text'].split('...')[1] + ' (' + yuan['time'] + ')'
        elif '……' in yuan_text:
            yuan_text1 = yuan['text'].split('……')[0] + ' (' + yuan['time'] + ')'
            yuan_text2 = yuan['text'].split('……')[1] + ' (' + yuan['time'] + ')'
        if yuan_text1:
            ask = get_id_list_promot_mode2(yuan_text1, zimu_union_text)
            keep_intervals = get_keeps_mode2(ask, zimu, yuan_text1, keep_intervals)
            ask = get_id_list_promot_mode2(yuan_text2, zimu_union_text)
            keep_intervals = get_keeps_mode2(ask, zimu, yuan_text2, keep_intervals)
        else:
            ask = get_id_list_promot_mode2(yuan_text, zimu_union_text)
            keep_intervals = get_keeps_mode2(ask, zimu, yuan_text, keep_intervals)

    print(f'AI:\nkeep_intervals：\n{keep_intervals}')
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
        # keep_intervals = [start_t, end_t, id_list, yuan_text]
        keep_intervals = get_intervals_by_ai_mode2([srt_list])
        interval = keep_intervals[0]
        if interval[0]:
            return interval[0], interval[1], interval[2], interval[3], 2
        debug = 1
    return None, None, None, None, None


def get_intervals_by_yuanwen(yuanwen, zimu_list):
    intervals = []
    for part in yuanwen:
        for yuan in part['zimu_list']:
            start = yuan['start']
            end = yuan['end']
            yuan_text = yuan['text']
            yuan_text = set_yuan_line(yuan_text)
            # keep_intervals = [start_t, end_t, id_list, yuan_text]
            start, end, id_list, zimu_str, zimu_mode = get_zimu_from_start_end(zimu_list, start, end, yuan_text)
            if start:
                intervals.append([start, end, id_list, zimu_str, zimu_mode])
            else:
                print(f'error: {yuan}')
                intervals.append([None, None, None, yuan_text, 0])
    keep_intervals, merged_list = merge_intervals(zimu_list, intervals)
    print(f'merge_keep_intervals=')
    for keep in keep_intervals:
        print(keep)
    print(f'merged_list={merged_list}')
    result = {'keep_intervals': keep_intervals, 'merged_intervals': merged_list}
    save_dict_to_json(result)
    return result
    
    
def get_intervals_by_mode2(wenan_content, zimu_list):
    yuanwen = get_yuanwen_mode2(wenan_content)
    result = get_intervals_by_yuanwen(yuanwen, zimu_list)
    return result