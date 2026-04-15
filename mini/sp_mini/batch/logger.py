import json
import os
from datetime import datetime


class BatchLogger:
    def __init__(self, log_file):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True) if os.path.dirname(
            log_file
        ) else None

    def log_phase(self, video_id, phase, iteration, duration_sec, status, **kwargs):
        entry = {
            "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "video_id": video_id,
            "phase": phase,
            "iteration": iteration,
            "duration_sec": round(duration_sec, 2),
            "status": status,
        }
        entry.update(kwargs)
        line = json.dumps(entry, ensure_ascii=False)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return entry

    def log_event(self, event, **kwargs):
        entry = {
            "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "event": event,
        }
        entry.update(kwargs)
        line = json.dumps(entry, ensure_ascii=False)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return entry
