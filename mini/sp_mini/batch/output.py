import sys
from datetime import datetime

import settings


def _now_text():
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")


def _emit(level, message, stream=None):
    if stream is None:
        stream = sys.stderr if level in ("WARN", "ERROR") else sys.stdout
    stream.write(f"{_now_text()} [{level}] {message}\n")
    stream.flush()


def info(message):
    _emit("INFO", message, sys.stdout)


def warn(message):
    _emit("WARN", message, sys.stderr)


def error(message):
    _emit("ERROR", message, sys.stderr)


def debug(message):
    if getattr(settings, "OUTPUT_DEBUG_ENABLED", False):
        _emit("DEBUG", message, sys.stdout)
