import sys
import threading
import time

from openai import OpenAI

import settings


SYSTEM_PROMPT = "You are a senior short video copywriter well-versed in the dissemination patterns of the TikTok platform."


def _make_client():
    return OpenAI(
        api_key=settings.BAILIAN_API_KEY,
        base_url="https://coding.dashscope.aliyuncs.com/v1",
        timeout=900,
    )


def call_llm_stream(prompt):
    client = _make_client()
    start = time.time()
    response = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )
    full = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            word = chunk.choices[0].delta.content
            sys.stdout.write(word)
            sys.stdout.flush()
            full += word
    sys.stdout.write("\n")
    sys.stdout.flush()
    print(f"[LLM] stream call duration: {round(time.time() - start, 2)} s")
    return full


def call_llm_batch(prompt, heartbeat_callback=None):
    stop_event = threading.Event()

    def _heartbeat():
        while not stop_event.wait(30):
            if heartbeat_callback:
                msg = heartbeat_callback()
                print(msg if msg else "[LLM] still waiting for response ...")
            else:
                print("[LLM] still waiting for response ...")

    heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
    heartbeat_thread.start()

    client = _make_client()
    start = time.time()
    try:
        response = client.chat.completions.create(
            model="qwen3.5-plus",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )
    finally:
        stop_event.set()
        heartbeat_thread.join(timeout=1)

    print(f"[LLM] batch call duration: {round(time.time() - start, 2)} s")
    return response.choices[0].message.content

