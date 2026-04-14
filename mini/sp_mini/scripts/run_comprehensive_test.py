#!/usr/bin/env python3
"""
run_comprehensive_test.py - 综合测试运行器

运行单视频和多视频模式的完整测试，收集性能数据
"""

import os
import sys
import json
import time
import argparse
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import settings
from batch_generator import scan_videos, process_video, process_multi_video
from batch.logger import BatchLogger


class Timer:
    """计时器"""

    def __init__(self, name):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time

    def __str__(self):
        return f"{self.name}: {self.duration:.2f}s"


class TestRunner:
    """测试运行器"""

    def __init__(self, mode="single", video_ids=None, output_dir=None):
        self.mode = mode
        self.video_ids = video_ids or []
        self.output_dir = output_dir or settings.BATCH_RESULTS_DIR
        self.results = {
            "test_date": datetime.now().isoformat(),
            "mode": mode,
            "video_ids": video_ids,
            "phases": {},
            "generated_videos": [],
            "errors": [],
            "warnings": [],
        }
        self.timings = {}
        self.min_multi_video_duration_sec = settings.BATCH_MIN_MULTI_VIDEO_DURATION_SEC

        # 配置测试模式
        settings.BATCH_TEST_MODE = True
        settings.BATCH_PHASE1_COUNT = getattr(settings, "BATCH_TEST_PHASE1_COUNT", 3)
        settings.BATCH_PHASE2_COUNT = getattr(settings, "BATCH_TEST_PHASE2_COUNT", 20)

        if mode == "multi":
            settings.BATCH_MULTI_VIDEO_ENABLE = True
        else:
            settings.BATCH_MULTI_VIDEO_ENABLE = False

    def run(self):
        """运行测试"""
        print("=" * 70)
        print(f"综合测试 - {self.mode.upper()} 视频模式")
        print("=" * 70)
        print()

        # 扫描视频
        with Timer("scan_videos") as t:
            videos = self._scan_and_filter_videos()
        self.timings["scan"] = t.duration

        if not videos:
            print("✗ 未找到视频文件")
            return False

        print(f"找到 {len(videos)} 个视频:")
        for vid, srt, mp4 in videos:
            print(f"  - {vid}")
        print()

        # 运行测试
        if self.mode == "single":
            success = self._run_single_video_test(videos)
        else:
            success = self._run_multi_video_test(videos)

        # 打印时间分析
        self._print_timing_analysis()

        # 生成报告
        self._generate_report()

        return success

    def _scan_and_filter_videos(self):
        """扫描并过滤视频"""
        all_videos = scan_videos(settings.DATA_DIR)

        if not self.video_ids:
            return all_videos

        # 过滤指定的视频 ID
        filtered = [
            (vid, srt, mp4) for vid, srt, mp4 in all_videos if vid in self.video_ids
        ]

        if not filtered:
            print(f"警告：未找到指定的视频 {self.video_ids}")
            return all_videos[:2]  # 返回前两个作为备选

        return filtered

    def _run_single_video_test(self, videos):
        """运行单视频测试"""
        print("开始单视频模式测试...")
        print()

        logger = BatchLogger(settings.BATCH_LOG_FILE)
        total_generated = 0
        for video_id, srt_path, mp4_path in videos:
            print(f"处理单视频源 {video_id} ...")
            with Timer(f"single_{video_id}_total") as t:
                try:
                    process_video(video_id, srt_path, mp4_path, logger)
                except Exception as e:
                    print(f"  ✗ {video_id} 处理失败：{e}")
                    self.results["errors"].append(f"{video_id}: {str(e)}")
                    continue
            self.timings[f"single_{video_id}_total"] = t.duration

            summary_path = os.path.join(self.output_dir, video_id, "summary.json")
            if os.path.exists(summary_path):
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary = json.load(f)
                generated = summary.get("generated_videos", [])
                total_generated += len(generated)
                self.results["generated_videos"].extend(generated)
                print(f"  ✓ {video_id}: 生成 {len(generated)} 个视频")
            else:
                self.results["warnings"].append(f"Summary missing for {video_id}")

        self.timings["single_video_total"] = sum(
            duration
            for name, duration in self.timings.items()
            if name.startswith("single_") and name.endswith("_total")
        )

        if total_generated <= 0:
            self.results["errors"].append("No single-video outputs generated")
            return False

        return True

    def _run_multi_video_test(self, videos):
        """运行多视频测试"""
        print("开始多视频模式测试...")
        print()

        logger = BatchLogger(settings.BATCH_LOG_FILE)

        # 运行多视频流程
        with Timer("multi_video_total") as t:
            try:
                process_multi_video(videos, logger)
                print("✓ 多视频流程完成")
            except Exception as e:
                print(f"✗ 多视频流程失败：{e}")
                self.results["errors"].append(f"Multi-video: {str(e)}")
                return False

        self.timings["multi_video_total"] = t.duration

        # 验证输出
        multi_dir = os.path.join(self.output_dir, "multi_video")

        if os.path.exists(multi_dir):
            # 检查 summary
            summary_path = os.path.join(multi_dir, "summary.json")
            if os.path.exists(summary_path):
                with open(summary_path, "r") as f:
                    summary = json.load(f)

                print(f"  ✓ Summary: {summary.get('total_candidates', 0)} 个候选")
                print(f"  ✓ 达标候选：{summary.get('qualified_candidates', 0)} 个")
                print(f"  ✓ 生成视频：{summary.get('videos_generated', 0)} 个")

                # 收集生成的视频信息
                for vid in summary.get("generated_videos", []):
                    self.results["generated_videos"].append(vid)

                if summary.get("videos_generated", 0) <= 0:
                    self.results["errors"].append(
                        f"No multi-video output reached {self.min_multi_video_duration_sec:.0f}s"
                    )
            else:
                print("  ✗ Summary 文件不存在")
                self.results["warnings"].append("Summary file not found")

            # 检查生成的视频
            gen_dir = os.path.join(multi_dir, "generated_videos")
            if os.path.exists(gen_dir):
                video_files = []
                for root, _, files in os.walk(gen_dir):
                    for fname in files:
                        if fname.endswith(".mp4"):
                            video_files.append(os.path.join(root, fname))
                print(f"  ✓ 视频目录：{len(video_files)} 个文件")
                for video_path in video_files:
                    duration = self._get_video_duration(video_path)
                    if duration < self.min_multi_video_duration_sec:
                        self.results["errors"].append(
                            f"Video shorter than {self.min_multi_video_duration_sec:.0f}s: {os.path.basename(video_path)} ({duration:.3f}s)"
                        )
            else:
                print("  ✗ 多视频输出目录不存在")
                self.results["warnings"].append("Multi-video output directory not found")

        return True

    def _get_video_duration(self, video_path):
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    video_path,
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return 0.0
            return float(result.stdout.strip() or 0)
        except Exception:
            return 0.0

    def _print_timing_analysis(self):
        """打印时间分析"""
        print()
        print("=" * 70)
        print("时间分析")
        print("=" * 70)

        total = sum(self.timings.values())

        print(f"\n{'阶段':<20} {'耗时 (s)':>12} {'占比':>10}")
        print("-" * 45)

        for phase, duration in sorted(
            self.timings.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (duration / total * 100) if total > 0 else 0
            print(f"{phase:<20} {duration:>12.2f} {percentage:>9.1f}%")

        print("-" * 45)
        print(f"{'总计':<20} {total:>12.2f} {100:>9.1f}%")

    def _generate_report(self):
        """生成测试报告"""
        self.results["timings"] = self.timings

        # 计算总时间
        self.results["total_duration"] = sum(self.timings.values())

        # 确定测试状态
        if self.results["errors"]:
            self.results["status"] = "FAILED"
        else:
            self.results["status"] = "PASSED"

        # 生成报告文件
        report_dir = os.path.join(settings.BATCH_RESULTS_DIR, "test_reports")
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(
            report_dir, f"test_report_{self.mode}_{timestamp}.json"
        )

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        # 生成 Markdown 报告
        md_path = report_path.replace(".json", ".md")
        self._generate_markdown_report(md_path)

        print()
        print(f"测试报告已生成:")
        print(f"  JSON: {report_path}")
        print(f"  Markdown: {md_path}")


def main():
    parser = argparse.ArgumentParser(description="综合测试运行器")
    parser.add_argument(
        "--mode",
        choices=["single", "multi"],
        default="single",
        help="测试模式：single=单视频，multi=多视频",
    )
    parser.add_argument(
        "--videos", nargs="+", default=[], help="指定视频 ID 列表（可选）"
    )
    parser.add_argument("--output-dir", default=None, help="输出目录（可选）")

    args = parser.parse_args()

    runner = TestRunner(
        mode=args.mode, video_ids=args.videos, output_dir=args.output_dir
    )

    success = runner.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
