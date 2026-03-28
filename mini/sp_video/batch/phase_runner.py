import os
import random
import time
import json
from main import run_phase1_batch, run_phase2_batch
from make_time.step2 import get_keep_intervals


def run_phase1_loop(video_id, srt_path, output_dir, count, logger):
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for i in range(count):
        output_path = os.path.join(output_dir, f"step1_{i+1:03d}.txt")
        start = time.time()
        try:
            content = run_phase1_batch(video_id, srt_path, output_path)
            duration = time.time() - start
            logger.log_phase(video_id, "phase1", i+1, duration, "success")
            results.append(output_path)
        except Exception as e:
            duration = time.time() - start
            logger.log_phase(video_id, "phase1", i+1, duration, "failed", reason=str(e))
    return results


def run_phase2_loop(video_id, phase1_files, output_dir, count, logger):
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for i in range(count):
        base_file = random.choice(phase1_files)
        with open(base_file, "r", encoding="utf-8") as f:
            phase1_content = f.read()
        output_path = os.path.join(output_dir, f"step2_{i+1:03d}.txt")
        start = time.time()
        try:
            content = run_phase2_batch(video_id, phase1_content, output_path)
            duration = time.time() - start
            logger.log_phase(video_id, "phase2", i+1, duration, "success")
            results.append(output_path)
        except Exception as e:
            duration = time.time() - start
            logger.log_phase(video_id, "phase2", i+1, duration, "failed", reason=str(e))
    return results


def run_phase3_loop(video_id, srt_path, phase2_files, output_dir, logger):
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for i, script_file in enumerate(phase2_files):
        with open(script_file, "r", encoding="utf-8") as f:
            script = f.read()
        start = time.time()
        try:
            result = get_keep_intervals(srt_path, script)
            intervals = result.get("keep_intervals", [])
            valid = [item for item in intervals if item[0][0]]
            if valid:
                output_path = os.path.join(output_dir, f"intervals_{i+1:03d}.json")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(valid, f, ensure_ascii=False, indent=2)
                duration = time.time() - start
                logger.log_phase(video_id, "phase3", i+1, duration, "success", matched=len(valid))
                results.append((i+1, valid))
            else:
                duration = time.time() - start
                logger.log_phase(video_id, "phase3", i+1, duration, "failed", reason="无有效片段")
        except Exception as e:
            duration = time.time() - start
            logger.log_phase(video_id, "phase3", i+1, duration, "failed", reason=str(e))
    return results
