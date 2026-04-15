"""
make_time/ai_caller.py — AI 调用封装 + JSON 解析 + 调试输出保存
"""
import json

import settings
from batch.output import debug, error

from .chat import ask_ai
from .prompts import build_check_similarity_prompt, build_find_subtitle_prompt
from .interval import is_consecutive, group_consecutive_ids, get_start_end_t_id_list


def parse_ai_json(result):
    """
    从 AI 返回字符串中提取第一个 { ... } 之间的合法 JSON。
    返回 dict 或 None。
    """
    try:
        start = result.index('{')
        end = len(result) - result[::-1].index('}') - 1
        return json.loads(result[start:end + 1])
    except (ValueError, json.JSONDecodeError) as e:
        error(f'parse_ai_json failed: {e}')
        debug(f'parse_ai_json raw={result}')
        return None


def save_result_to_json(result, filename="keep_intervals.json"):
    """将匹配结果写入调试文件。"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        debug(f"已写入 {filename}")
    except Exception as e:
        error(f"写入 {filename} 失败: {e}")


def call_ai_match(ask, zimu, yuan_text, model_name):
    """
    第一阶段匹配：调用 AI 返回 id_list，再做相似度验证。
    验证通过则按连续分组返回区间列表；未通过返回 [[None, None, None, None]]。
    """
    raw = ask_ai(ask, mod=model_name, json_format=True)
    debug(f'AI match result: {raw}')
    result = parse_ai_json(raw)
    if not result:
        return [[None, None, None, None]]

    id_list = result.get('id_list', [])
    result_text = result.get('text', '')

    clean_yuan = yuan_text.split(' (')[0] if ' (' in yuan_text else yuan_text

    check_ask = build_check_similarity_prompt(clean_yuan, result_text)
    raw2 = ask_ai(check_ask, mod=model_name, json_format=True)
    debug(f'AI similarity result: {raw2}')
    result2 = parse_ai_json(raw2)
    if not result2:
        return [[None, None, None, None]]

    probability = result2.get('probability', 0)
    if is_consecutive(id_list):
        probability += settings.AI_CONSECUTIVE_BONUS
        debug(f'consecutive bonus applied, probability={probability}')

    if probability > settings.AI_CHECK_THRESHOLD:
        debug(f'probability ok => {probability}')
        return [get_start_end_t_id_list(zimu, g) for g in group_consecutive_ids(id_list)]

    debug(f'probability ng => {probability} | yuan_text={yuan_text}')
    return [[None, None, None, None]]


def call_ai_find(ask, yuan_text, model_name):
    """
    降级阶段：全文语义搜索，返回 id_list（不做相似度截断）。
    """
    raw = ask_ai(ask, mod=model_name, json_format=True)
    debug(f'AI find ask={ask}')
    debug(f'AI find result={raw}')
    result = parse_ai_json(raw)
    if not result:
        return None

    id_list = result.get('id_list')
    result_text = result.get('text', '')
    check_ask = build_check_similarity_prompt(yuan_text, result_text)
    raw2 = ask_ai(check_ask, mod=model_name, json_format=True)
    result2 = parse_ai_json(raw2)
    probability = result2.get('probability', 0) if result2 else 0
    debug(f'find probability => {probability}')
    return id_list


def find_intervals_by_ai(yuan_text, zimu, model_name):
    """
    降级入口：用 build_find_subtitle_prompt 构造全文搜索 prompt，返回 id_list。
    """
    zimu_union_text = ''.join(
        f'{zid}\n{s} --> {e}\n{txt}\n\n\n'
        for zid, (s, e), txt in zimu
    )
    ask = build_find_subtitle_prompt(yuan_text, zimu_union_text)
    id_list = call_ai_find(ask, yuan_text, model_name)
    return id_list
