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


BATCH_PHASE1_COUNT = 20
BATCH_PHASE2_COUNT = 100
BATCH_SCORE_THRESHOLD = 7.0
BATCH_MIN_MULTI_VIDEO_DURATION_SEC = 18.0
BATCH_RESULTS_DIR = "./data/batch_results"
BATCH_LOG_FILE = "./data/batch_log.jsonl"

BATCH_SINGLE_VIDEO_TARGET_PER_SOURCE = 10
BATCH_MULTI_VIDEO_TARGET_COUNT = 100
BATCH_MULTI_VIDEO_CANDIDATE_COUNT = 150

# 时长桶概率配置。
# 概率用于“尽量按分布采样”，实际生成数会受候选数量影响。
BATCH_DURATION_BUCKETS = [
    {"label": "20-30s", "min_sec": 20, "max_sec": 30, "probability": 0.12},
    {"label": "30-45s", "min_sec": 30, "max_sec": 45, "probability": 0.18},
    {"label": "45-60s", "min_sec": 45, "max_sec": 60, "probability": 0.30},
    {"label": "60-90s", "min_sec": 60, "max_sec": 90, "probability": 0.20},
    {"label": "90-120s", "min_sec": 90, "max_sec": 120, "probability": 0.12},
    {"label": "120-300s", "min_sec": 120, "max_sec": 300, "probability": 0.08},
]

BATCH_VISUAL_ENABLE = False
BATCH_VISUAL_TOPN = 2
BATCH_VISUAL_SAMPLE_EVERY_SEC = 2
BATCH_VISUAL_MAX_FRAMES = 9
BATCH_VISUAL_USE_LLM = False

BATCH_TRANSITION_ENABLE = False

# 多视频输出仍处于验收加固阶段。
# 默认保持关闭，只有明确需要验收或生产启用时再手动打开。
BATCH_MULTI_VIDEO_ENABLE = False

# 测试模式：降低批量参数用于快速验证
# 注意：生产环境请保持 False，测试时临时改为 True
BATCH_TEST_PHASE1_COUNT = 3
BATCH_TEST_PHASE2_COUNT = 20
BATCH_TEST_MODE = False
if BATCH_TEST_MODE:
    BATCH_PHASE1_COUNT = BATCH_TEST_PHASE1_COUNT
    BATCH_PHASE2_COUNT = BATCH_TEST_PHASE2_COUNT
