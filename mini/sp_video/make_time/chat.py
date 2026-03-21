import os
import time
from openai import OpenAI
import settings

ask_dic = {
    'cost': 0
}


def ask_ai(ask, mod, json_format=False):
    deepseek_api_key = settings.DEEPSEEK_API_KEY
    system_prompt = 'You are a helpful assistant.'


    client, model_name = None, None
    # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    if mod == 'deepseek-r1-70b':
        # 需要 BAILIAN_API_KEY 时请使用环境变量 BAILIAN_API_KEY
        bailian_api_key = os.environ.get("BAILIAN_API_KEY", "")
        model_name = 'deepseek-r1-distill-llama-70b'
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        client = OpenAI(
            api_key=bailian_api_key,
            base_url=url,
        )
    elif mod == 'deepseek-r1':
        # 需要 BAILIAN_API_KEY 时请使用环境变量 BAILIAN_API_KEY
        bailian_api_key = os.environ.get("BAILIAN_API_KEY", "")
        model_name = 'deepseek-r1-0528'
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        client = OpenAI(
            api_key=bailian_api_key,
            base_url=url,
        )
    elif mod == 'deepseek':
        model_name = 'deepseek-chat'
        url = "https://api.deepseek.com"
        client = OpenAI(
            api_key=deepseek_api_key,
            base_url=url,
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