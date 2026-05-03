import argparse
import os

import dashscope
import requests
from dashscope import MultiModalConversation


dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
API_KEY = os.getenv('DASHSCOPE_API_KEY') or 'sk-750aa7d1e95f468197a330fe9f6e6782'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--out')
    args = parser.parse_args()

    out = args.out or os.path.join('imgs', 'draw.png')
    if os.path.exists(out):
        print(out)
        return

    response = MultiModalConversation.call(
        api_key=API_KEY,
        model='qwen-image-2.0-2026-03-03',
        messages=[{'role': 'user', 'content': [{'text': args.prompt}]}],
        result_format='message',
        stream=False,
        watermark=False,
        prompt_extend=True,
        size='2048*2048'
    )
    if response.status_code != 200:
        raise RuntimeError(f'{response.code}: {response.message}')

    image_url = response.output.choices[0].message.content[0]['image']
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'wb') as f:
        f.write(requests.get(image_url, timeout=300).content)
    print(out)


if __name__ == '__main__':
    main()
