import json
import os
import time

from shared.file_lock import file_lock


def now_text():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def default_worker_id(worker_id=None):
    return worker_id if worker_id else f"pid-{os.getpid()}"


def load_tasks(task_file):
    if not os.path.exists(task_file):
        return {}
    with open(task_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(task_file, tasks):
    task_dir = os.path.dirname(task_file)
    if task_dir:
        os.makedirs(task_dir, exist_ok=True)
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def init_tasks(task_file, video_pairs, force=False):
    lock_path = task_file + ".lock"
    with file_lock(lock_path):
        if os.path.exists(task_file) and not force:
            return False, load_tasks(task_file)

        tasks = {}
        for video_id, srt_path, mp4_path in video_pairs:
            tasks[video_id] = {
                "status": "pending",
                "stage": None,
                "worker_id": None,
                "srt_path": srt_path,
                "mp4_path": mp4_path,
                "started_at": None,
                "updated_at": None,
                "ended_at": None,
                "output_video": None,
                "error": None,
            }
        save_tasks(task_file, tasks)
        return True, tasks


def claim_next_task(task_file, worker_id=None):
    worker = default_worker_id(worker_id)
    lock_path = task_file + ".lock"
    with file_lock(lock_path):
        tasks = load_tasks(task_file)
        for video_id in sorted(tasks):
            task = tasks[video_id]
            if task.get("status") != "pending":
                continue
            now = now_text()
            task["status"] = "running"
            task["stage"] = "running"
            task["worker_id"] = worker
            task["started_at"] = now
            task["updated_at"] = now
            task["ended_at"] = None
            task["error"] = None
            save_tasks(task_file, tasks)
            return video_id, task
    return None, None


def update_task(task_file, video_id, status=None, stage=None, output_video=None, error=None):
    lock_path = task_file + ".lock"
    with file_lock(lock_path):
        tasks = load_tasks(task_file)
        if video_id not in tasks:
            tasks[video_id] = {}

        task = tasks[video_id]
        now = now_text()
        if status is not None:
            task["status"] = status
        if stage is not None:
            task["stage"] = stage
        task["updated_at"] = now

        if status in ("completed", "failed", "skipped"):
            task["ended_at"] = now
        if output_video is not None:
            task["output_video"] = output_video
        if error is not None:
            task["error"] = error

        save_tasks(task_file, tasks)
        return task

