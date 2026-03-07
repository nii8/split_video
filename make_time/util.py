import json
import re
import sys
from .chat import ask_ai
from datetime import datetime

def set_yuan_line(line):
    line = line.strip()
    if line.startswith(('“', '"')):
        line = line[1:]
    line = line.strip()
    if line.endswith(('”', '"')):
        line = line[:-1]
    return line


def remove_milliseconds(time_list):
    """
    去除时间戳中的毫秒部分
    例如：['00:00:01,733 ', ' 00:00:02,300'] -> ['00:00:01', '00:00:02']

    Args:
        time_list (list): 包含时间戳字符串的列表

    Returns:
        list: 去除毫秒后的时间戳列表
    """
    cleaned_list = []
    for time_str in time_list:
        # 去除首尾空格
        stripped = time_str.strip()
        # 分割并取第一部分（去掉逗号后的毫秒）
        without_ms = stripped.split(',')[0]
        cleaned_list.append(without_ms)
    return cleaned_list


# ge 格式
def is_start_bigger_end(start: str, end: str) -> bool:
    """
    比较两个时间戳，判断 start 是否 >= end。
    支持格式：
    - HH:MM:SS
    - HH:MM:SS,fff
    - HH:MM:SS.fff

    Args:
        start (str): 起始时间（如 '00:00:06,300'）
        end (str): 结束时间（如 '00:00:15'）

    Returns:
        bool: 如果 start >= end 返回 True，否则 False
    """
    # 统一替换可能的毫秒分隔符（, 或 .）
    start_clean = start.replace(',', '.')
    end_clean = end.replace(',', '.')

    # 解析时间（支持带/不带毫秒）
    fmt = "%H:%M:%S.%f" if '.' in start_clean else "%H:%M:%S"
    start_time = datetime.strptime(start_clean, fmt)

    fmt = "%H:%M:%S.%f" if '.' in end_clean else "%H:%M:%S"
    end_time = datetime.strptime(end_clean, fmt)

    return start_time >= end_time


def get_zimu_index_list_by_time(zimu_list, yuan):
    yuan_text = yuan["text"]
    yuan_time = yuan["time"]
    yuan_len = len(yuan_text)
    ok_index = None
    start_index = None
    end_index = None
    for index, zimu in enumerate(zimu_list):
        zimu_t = remove_milliseconds(zimu[1])
        start_time, end_time = zimu_t
        # 开始时间是否比结束时间大
        if is_start_bigger_end(start_time, yuan_time):
            ok_index = zimu[0]
            zimu_text = zimu[2]
            zimu_len = len(zimu_text)
            yuan_cp_len = 0
            for i in range(20):
                if index - i - 1 > 0:
                    child = zimu_list[index - i - 1]
                    child_len = len(child[2])
                    yuan_cp_len += child_len
                    if yuan_cp_len > yuan_len * 2 and i > 10:
                        start_index = child[0]
                        break
            if not start_index:
                start_index = ok_index - 5
                if start_index <= 1:
                    start_index = 1
            yuan_cp_len = 0
            for i in range(20):
                if index + i < len(zimu_list) - 1:
                    child = zimu_list[index + i]
                    child_len = len(child[2])
                    yuan_cp_len += child_len
                    if yuan_cp_len > yuan_len * 2 and i > 10:
                        end_index = child[0]
                        break
            if not end_index:
                end_index = ok_index + 5
                if end_index >= len(zimu_list):
                    end_index = len(zimu_list)
            break
    mini_zimu_list = []
    if start_index is None or end_index is None:
        return mini_zimu_list
    for zimu in zimu_list:
        zimu_id = zimu[0]
        if start_index <= zimu_id <= end_index:
            mini_zimu_list.append(zimu)
    return mini_zimu_list


def get_ai_json(result):
    """
    从字符串中提取第一个 { 到最后一个 } 之间的内容，确保返回合法JSON

    参数:
        result (str): 可能包含多余内容的字符串

    返回:
        str: 提取出的合法JSON字符串

    示例:
        result = "废话...{'key':'value'}...更多废话"
        get_ai_json(result)
        '{"key":"value"}'
    """
    try:
        # 找到第一个 { 的索引
        start = result.index('{')
        # 找到最后一个 } 的索引（从末尾向前找）
        end = len(result) - result[::-1].index('}') - 1

        # 提取目标内容
        json_str = result[start:end + 1]

        # 验证是否为合法JSON（可选）
        json_ret = json.loads(json_str)  # 如果解析失败会抛出异常

        return json_ret
    except ValueError as e:
        print(f'error: 无法找到有效的JSON边界 {{ }} {result}')
        return None
    except Exception as e:
        print(f'提取的内容不是合法JSON: {result}')
        return None


def get_check_promot(result_text, yuan_text):
    ask = f'''请比较2个句子的相似性，输出结构化JSON数据：
# 处理规则
1. 输入数据：
   - [句子1]：输入的句子
   - [句子2]：输入的句子

2. 匹配要求：
   - 比较[句子1]和[句子2]的相似程度

3. JSON格式规范：
   - 条目包含：
     * probability: [句子1]和[句子2]的相似程度, 范围[0.0-1.0], 百分百相似输出1.0, 保留2位小数

# 示例输入：

[句子1]：因为在上市公司我 我做事做得很好 我在那都是做的最好的 但是这个呃 那时候会觉得 这好像都是自己的能力 其实有很多是平台的能力
[句子2]：因为在上市公司我做事做得很好，我在那都是做的最好的，但是那个时候会觉得这好像都是自己的能力，其实有很多是平台的能力

[正确输出]
{{"probability": 0.95}}

# 示例输入2：

[句子1]：SWOT是极小极小的工具
[句子2]：sort是一个极小极小 极小的工具

[正确输出]
{{"probability": 0.89}}

示例输入2的解释：因为句子2是字幕文件获取, 如果说话不标准或者发音问题或者翻译问题, 
导致字幕把真实要表达的SWOT翻译成了sort, 所以输出概率会有一个补偿


# 待处理数据
[句子1]
{result_text}

[句子2]
{yuan_text}

请严格按照示例格式输出JSON，确保：
1. 不使用换行符或特殊分隔符'''
    return ask



def is_consecutive(lst):
    """检查整数列表是否连续（允许正序或倒序）"""
    if len(lst) <= 1:
        return True
    sorted_lst = sorted(lst)
    return sorted_lst == list(range(sorted_lst[0], sorted_lst[-1] + 1))


def group_consecutive_ids(id_list):
    """
    将连续的ID分组，保持原始顺序

    Args:
        id_list: 整数列表，如 [3,1,2,7]

    Returns:
        list: 分组后的列表，如 [[3], [1,2], [7]]
    """
    if not id_list:
        return []

    result = []
    current_group = [id_list[0]]

    for i in range(1, len(id_list)):
        current_id = id_list[i]
        prev_id = id_list[i - 1]

        # 检查是否连续（当前ID比前一个ID大1）
        if current_id == prev_id + 1:
            current_group.append(current_id)
        else:
            # 不连续，开始新的分组
            result.append(current_group)
            current_group = [current_id]

    # 添加最后一个分组
    result.append(current_group)

    return result


def get_start_end_t_id_list(zimu, id_list):
    start_t = None
    end_t = None
    unit_zimu = ''
    for zimu_id, (start, end), zimu_str, in zimu:
        if zimu_id == id_list[0]:
            start_t = start
        if zimu_id == id_list[-1]:
            end_t = end
        for unit_id in id_list:
            if unit_id == zimu_id:
                unit_zimu = unit_zimu + ' ' + zimu_str
    if start_t and end_t:
        # print(f'cur interval= [{start_t}, {end_t}]')
        return [start_t, end_t, id_list, unit_zimu]
    else:
        print(f'error start_t={start_t}, end_t={end_t}')
        return [None, None, None, None]


def get_unit_interval_by_ai(ask, zimu, yuan_text, ask_modal_name, check_probability):
    result = ask_ai(ask, mod=ask_modal_name, json_format=True)
    # print(f'ask={ask}')
    print(f'result={result}')
    result = get_ai_json(result)
    id_list = result.get('id_list')
    result_text = result.get('text')
    if ' (' in yuan_text:
        yuan_text = yuan_text.split(' (')[0]
    check_ask = get_check_promot(yuan_text, result_text)
    result2 = ask_ai(check_ask, mod=ask_modal_name, json_format=True)
    print(f'check_ask={check_ask}')
    print(f'result={result2}')
    result2 = get_ai_json(result2)
    probability = result2.get('probability')
    if is_consecutive(id_list):
        probability += 0.05
        print(f'is_consecutive {id_list} is 连续的 probability = {probability}')
    if probability and probability > check_probability:
        print(f'probability ok => {probability}')
    else:
        print(f'probability ng => {probability} yuan_text => {yuan_text}')
        return [[None, None, None, None]]
    group_id_list = group_consecutive_ids(id_list)
    unit_intervals = []
    for group_id in group_id_list:
        unit = get_start_end_t_id_list(zimu, group_id)
        unit_intervals.append(unit)
    return unit_intervals



def check_timeline_format(line):
    """
    检查字符串是否符合时间轴格式并提取时间戳
    00:00:53,900 --> 00:00:56,500
    参数:
        line (str): 要检查的字符串

    返回:
        tuple: (bool, list)
               - 第一个元素表示是否匹配格式 (True/False)
               - 第二个元素是提取的两个时间戳 (如果匹配) 或 [None, None]
    """
    pattern = r'^(\d{2}:\d{2}:\d{2},\d{3})\s-->\s(\d{2}:\d{2}:\d{2},\d{3})$'
    match = re.fullmatch(pattern, line.strip())

    if match:
        return True, [match.group(1), match.group(2)]
    else:
        return False, [None, None]



def merge_intervals(filter_zimu_list, keep_intervals):
    # filter_zimu_list  [num, [start, end], text]
    # keep_intervals = [start_t, end_t, id_list, yuan_text, zimu_mode]
    # 构建 num 到 time_duration 的映射
    num_to_time = {}
    for item in filter_zimu_list:
        num = item[0]
        start, end = item[1]
        num_to_time[num] = (start, end)

    merged = []
    merged_list = []
    i = 0
    n = len(keep_intervals)

    while i < n:
        current_start, current_end, cur_id_list, cur_text, cur_zimu_mode = keep_intervals[i]
        if cur_zimu_mode:
            cur_text += f'[[mode={cur_zimu_mode}]]'

        j = i + 1
        if current_start and current_end:
            # 检查是否可以合并
            while j < n:
                next_start, next_end, next_id_list, next_text, next_mode = keep_intervals[j]

                # 检查 num 是否连续
                num_continuous = False
                # 找到 current_end 对应的 num
                current_num = None
                next_num = None
                for num, (start, end) in num_to_time.items():
                    if end.strip() == current_end:
                        current_num = num
                    if start.strip() == next_start:
                        next_num = num
                if current_num is not None and next_num is not None:
                    num_continuous = (next_num == current_num + 1)

                # 如果时间和 num 都连续，则合并
                if num_continuous:
                    current_end = next_end
                    if next_mode:
                        next_text += f'[[mode={next_mode}]]'

                    cur_text = cur_text + ' ' + next_text

                    j += 1
                else:
                    break

        merged.append([[current_start, current_end], cur_text])
        merged_list.append([current_start, current_end])
        i = j

    return merged, merged_list

def save_dict_to_json(result, filename="keep_intervals.json"):
    """
    将字典写入 JSON 文件

    参数:
        result (dict): 要保存的字典数据
        filename (str): 保存的文件名（默认: keep_intervals.json）
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"字典已成功写入 {filename}")
    except Exception as e:
        print(f"写入文件时出错: {e}")


def get_zimu_range_by_time(zimu_list, y_start_time):
    for index, zimu in enumerate(zimu_list):
        zimu_t = remove_milliseconds(zimu[1])
        z_start_time, _ = zimu_t
        if is_start_bigger_end(z_start_time, y_start_time):
            ok_index = zimu[0]
            start_index = ok_index-50
            if start_index <= 1:
                start_index = 1
            end_index = ok_index+50
            if end_index >= len(zimu_list):
                end_index = len(zimu_list)
            return zimu_list[start_index:end_index]
    return None


def get_id_list_promot_v2(yuan_text, zimu_union_text):
    ask = f'''请根据以下规则整理出与原文句子相关的时间序列并生成结构化JSON数据：
# 处理规则
1. 输入数据：
   - [时间序列]：字幕片段（含字幕id,时间戳和文本）
   - [原文句子]：需要匹配的目标句子

2. 匹配要求：
   - 假如原文句子是[企业扩张时要学会就地取材解决补给问题]
   - 在时间序列里面找若干个子序列拼接后变成一个拼接的句子, 比如: [403, '所以一个企业'], [406, '尤其要扩张时候'], [410, '一定要学会'], [433, '就地取材'], [379, '他是彻底的解决补给问题']
   - 原文句子[企业扩张时要学会就地取材解决补给问题]和拼接后句子[所以一个企业 尤其要扩张时候 一定要学会 就地取材 他是彻底的解决补给问题] 在语义上是很匹配相似的
   - 最后输出id_list是[403,406,410,433,379] text是[所以一个企业 尤其要扩张时候 一定要学会 就地取材 他是彻底的解决补给问题]
3. JSON格式规范：
   - 条目包含：
     * id_list: 和原文句子匹配的字幕的id列表（顺序与下面的文本text对应）
     * text: 拼接后的完整文本（用空格连接片段）

# 示例输入：

[原文句子]
企业扩张时要学会就地取材解决补给问题

[时间序列]
348
00:09:58,066 --> 00:09:58,900
这为什么

349
00:09:59,100 --> 00:09:59,833
其实蒙古

350
00:09:59,833 --> 00:10:01,233
解决了一个最根本的问题

351
00:10:02,000 --> 00:10:03,400
就是补给的问题

352
00:10:03,933 --> 00:10:04,600
粮草粮草

353
00:10:04,600 --> 00:10:05,433
补给的问题

354
00:10:05,966 --> 00:10:06,866
他们是那个什么

355
00:10:06,866 --> 00:10:08,400
就是呃一个

356
00:10:08,400 --> 00:10:10,200
一个军人是呃

375
00:10:39,300 --> 00:10:40,333
马杀掉作为

376
00:10:40,333 --> 00:10:42,300
作为作为那个呃

377
00:10:42,300 --> 00:10:42,900
军粮

378
00:10:42,900 --> 00:10:45,300
所以他就蒙古是解决了

379
00:10:45,433 --> 00:10:47,000
他是彻底的解决补给问题

380
00:10:47,000 --> 00:10:48,533
所以他可以纵横天下

381
00:10:48,633 --> 00:10:51,066
到哪就那个就地取材

382
00:10:51,200 --> 00:10:52,866
一个是他自个有个备份的马

383
00:10:52,866 --> 00:10:54,233
一个呢就地取材吃

390
00:11:08,000 --> 00:11:09,633
就是蒙古人其实就干的这个

391
00:11:09,633 --> 00:11:12,866
因因粮于敌就是就地取材

392
00:11:13,433 --> 00:11:14,900
打到哪吃到哪

393
00:11:15,533 --> 00:11:17,066
解决那个后勤的问题

394
00:11:17,066 --> 00:11:20,266
而不是说从我老本

395
00:11:20,333 --> 00:11:21,466
那个老家去

398
00:11:24,333 --> 00:11:25,800
你看当时宋朝都是

399
00:11:25,933 --> 00:11:27,333
当时得补那么长的

400
00:11:27,600 --> 00:11:28,533
所以这就是麻烦

401
00:11:28,533 --> 00:11:28,866
所以

402
00:11:28,866 --> 00:11:30,866
蒙古人就是解决这个问题

403
00:11:30,933 --> 00:11:31,666
所以一个企业

404
00:11:31,666 --> 00:11:33,066
如果你已经做到

405
00:11:34,200 --> 00:11:35,200
已经度过了生存期

406
00:11:35,200 --> 00:11:36,300
尤其要扩张时候

407
00:11:36,300 --> 00:11:37,633
或者开拓新市场的时候

408
00:11:37,633 --> 00:11:39,100
这个时候就特别重要

409
00:11:39,100 --> 00:11:39,633
需要什么

410
00:11:39,633 --> 00:11:40,266
一定要学会

411
00:11:40,266 --> 00:11:41,333
就是要知道

412
00:11:41,533 --> 00:11:42,400
初创的时候

413
00:11:42,400 --> 00:11:44,233
和你要开拓新市场的时候

414
00:11:44,233 --> 00:11:46,866
都是要一定要记得兵草呃

415
00:11:46,866 --> 00:11:48,200
那个兵马未动

416
00:11:48,333 --> 00:11:48,866
粮草先行

417
00:11:48,866 --> 00:11:50,133
你把这事得想好了

418
00:11:50,133 --> 00:11:51,533
要不你扩张的时候

419
00:11:51,700 --> 00:11:52,600
最终跟不上

429
00:12:05,900 --> 00:12:07,866
如果能够学习蒙古人

430
00:12:09,033 --> 00:12:11,200
你解决这个就地取材的问题

431
00:12:11,233 --> 00:12:13,266
其实大家去看好多商

432
00:12:13,266 --> 00:12:15,200
业的成功都是就地取材

433
00:12:15,700 --> 00:12:16,633
就地取材

434
00:12:16,666 --> 00:12:18,666
然后扎根于当地

435
00:12:18,800 --> 00:12:20,000
才能够成功的

[正确输出]
{{
    "id_list": [403, 406, 410, 433, 379],
    "text": "所以一个企业 尤其要扩张时候 一定要学会 就地取材 他是彻底的解决补给问题"
}}

# 待处理数据
[原文句子]
{yuan_text}

[时间序列]
{zimu_union_text}

请严格按照示例格式输出JSON，确保：
1. id_list里面的id要仔细核对和时间序列里面的id一致
2. 拼接后的text 和 原文句子是匹配的
3. 文本内容用单个空格连接片段
4. 不使用换行符或特殊分隔符'''
    return ask


def get_find_interval_by_ai(ask, yuan_text, ask_modal_name):
    result = ask_ai(ask, mod=ask_modal_name, json_format=True)
    print(f'ask={ask}')
    print(f'result={result}')
    result = get_ai_json(result)
    result_text = result.get('text')
    id_list = result.get('id_list')
    check_ask = get_check_promot(yuan_text, result_text)
    result2 = ask_ai(check_ask, mod=ask_modal_name, json_format=True)
    print(f'check_ask={check_ask}')
    print(f'result={result2}')
    result2 = get_ai_json(result2)
    probability = result2.get('probability')
    print(f'find probability => {probability}')
    return id_list


def get_intervals_by_ai_find(yuan_text, zimu, ask_modal_name):
    zimu_union_text = ''
    for zimu_id, (start, end), zimu_str, in zimu:
        zimu_union_text = zimu_union_text + f'{zimu_id}\n{start} --> {end}\n{zimu_str}\n\n\n'
    ask = get_id_list_promot_v2(yuan_text, zimu_union_text)
    id_list = get_find_interval_by_ai(ask, yuan_text, ask_modal_name)
    return id_list