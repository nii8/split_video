import time
from openai import OpenAI
import settings

ask_dic = {
    'cost': 0
}


def ask_ai(ask, mod, json_format=False):
    deepseek_api_key = settings.DEEPSEEK_API_KEY
    bailian_api_key = settings.BAILIAN_API_KEY
    system_prompt = 'You are a helpful assistant.'

    client, model_name = None, None
    # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    if mod == 'qwen':
        model_name = 'qwen3.5-plus'
        client = OpenAI(
            api_key=bailian_api_key,
            base_url="https://coding.dashscope.aliyuncs.com/v1",
            timeout=900,  # 15分钟超时
        )
    elif mod == 'deepseek-r1-70b':
        model_name = 'deepseek-r1-distill-llama-70b'
        client = OpenAI(
            api_key=bailian_api_key,
            base_url="https://coding.dashscope.aliyuncs.com/v1",
            timeout=900,  # 15分钟超时
        )
    elif mod == 'deepseek-r1':
        model_name = 'deepseek-r1-0528'
        client = OpenAI(
            api_key=bailian_api_key,
            base_url="https://coding.dashscope.aliyuncs.com/v1",
            timeout=900,  # 15分钟超时
        )
    elif mod == 'deepseek':
        model_name = 'deepseek-chat'
        url = "https://api.deepseek.com"
        client = OpenAI(
            api_key=deepseek_api_key,
            base_url=url,
            timeout=900,  # 15分钟超时
        )
    try:

        ask_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": ask},
        ]
        t1 = time.time()

        if json_format:
            completion = client.chat.completions.create(model=model_name, messages=ask_messages,
                                                        response_format={'type': 'json_object'})
        else:
            completion = client.chat.completions.create(model=model_name, messages=ask_messages)
        t2 = time.time()
        ask_dic['cost'] += round(t2 - t1, 2)
        print(f'AI cost:{round(t2 - t1, 2)} sec')
        print(f"\033[31m total:{ask_dic['cost']} sec \033[0m")

        return completion.choices[0].message.content
    except Exception as e:
        print(f"错误信息：{e}")
        print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")