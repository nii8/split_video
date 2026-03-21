"""
settings.py — 全局配置中心

所有常量都在这里定义，支持环境变量覆盖（方便部署）。
其他文件统一 import settings 来读取配置。
"""
import os
import yaml
import json


# ── 网络 ─────────────────────────────────────────────────────────────────────
SERVER_IP    = os.environ.get("SERVER_IP",   "113.249.103.24")
WORKER_IPS   = os.environ.get("WORKER_IPS",  "113.249.107.180,113.249.107.182").split(",")
UPLOAD_TOKEN = os.environ.get("UPLOAD_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0N")

# ── 端口 ─────────────────────────────────────────────────────────────────────
BASE_SSE_PORT  = 5001
BACKEND_COUNT  = 16
WORKER_PORT    = 8868

# ── AI 参数 ──────────────────────────────────────────────────────────────────
LIMIT_PROMPT         = 8192   # 最大 token 数
AI_CHECK_THRESHOLD   = 0.88   # 相似度验证通过线
AI_CONSECUTIVE_BONUS = 0.05   # 连续 ID 加分

# ── 后端状态 ─────────────────────────────────────────────────────────────────
BACKEND_IDLE_SEC = 180   # 超过此秒数视为空闲

# ── 数据目录 ─────────────────────────────────────────────────────────────────
DATA_DIR = os.environ.get("DATA_DIR", "./data/hanbing")


# ── 从配置文件加载 API Key ────────────────────────────────────────────────────
def _load_yaml():
    try:
        with open('./data/config/config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _load_json():
    try:
        with open('./data/config/config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


_yaml = _load_yaml()
_cfg  = _load_json()

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", _yaml.get("DEEPSEEK_API_KEY", ""))
BAILIAN_API_KEY  = os.environ.get("BAILIAN_API_KEY",  _yaml.get("BAILIAN_API_KEY",  ""))

TOKEN_LIST = _cfg.get("token_list", [])
NAME_DIC   = _cfg.get("name_dic",   {})
