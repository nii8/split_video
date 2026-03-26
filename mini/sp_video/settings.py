"""
settings.py — 全局配置中心

所有常量都在这里定义。
其他文件统一 import settings 来读取配置。
"""

import yaml


# ── 网络 ─────────────────────────────────────────────────────────────────────
SERVER_IP = "113.249.103.24"
WORKER_IPS = ["113.249.107.180", "113.249.107.182"]
UPLOAD_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0N"

# ── 端口 ─────────────────────────────────────────────────────────────────────
BASE_SSE_PORT = 5001
BACKEND_COUNT = 16
WORKER_PORT = 8868

# ── AI 参数 ──────────────────────────────────────────────────────────────────
LIMIT_PROMPT = 8192  # 最大 token 数
AI_CHECK_THRESHOLD = 0.88  # 相似度验证通过线
AI_CONSECUTIVE_BONUS = 0.05  # 连续 ID 加分

# ── 后端状态 ─────────────────────────────────────────────────────────────────
BACKEND_IDLE_SEC = 180  # 超过此秒数视为空闲

# ── 数据目录 ─────────────────────────────────────────────────────────────────
DATA_DIR = "./data/hanbing"

# ── 视频切割 ─────────────────────────────────────────────────────────────────
KEYFRAME_THRESHOLD = 0.2  # 关键帧距离阈值（秒），小于此值用 copy 模式


# ── 从配置文件加载 API Key ────────────────────────────────────────────────────
def _load_yaml():
    try:
        with open("./data/config/config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


_yaml = _load_yaml()

DEEPSEEK_API_KEY = _yaml.get("DEEPSEEK_API_KEY", "")
BAILIAN_API_KEY = _yaml.get("BAILIAN_API_KEY", "")
