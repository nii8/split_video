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

        # 配置测试模式
        settings.BATCH_TEST_MODE = True
        settings.BATCH_PHASE1_COUNT = 1
        settings.BATCH_PHASE2_COUNT = 1

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

        # 只测试第一个视频
        video_id, srt_path, mp4_path = videos[0]

        logger = BatchLogger(settings.BATCH_LOG_FILE)

        # Phase 1
        print("Phase 1: 字幕筛选")
        with Timer("phase1") as t:
            try:
                from batch.phase_runner import run_phase1_loop

                phase1_dir = os.path.join(self.output_dir, video_id, "phase1")
                phase1_files = run_phase1_loop(
                    video_id, srt_path, phase1_dir, 1, logger
                )
                success = len(phase1_files) > 0
                print(f"  {'✓' if success else '✗'} Phase1: {len(phase1_files)} 个结果")
            except Exception as e:
                print(f"  ✗ Phase1 失败：{e}")
                self.results["errors"].append(f"Phase1: {str(e)}")
                return False

        self.timings["phase1"] = t.duration

        # Phase 2
        print("Phase 2: 脚本生成")
        with Timer("phase2") as t:
            try:
                from batch.phase_runner import run_phase2_loop

                phase2_dir = os.path.join(self.output_dir, video_id, "phase2")
                phase2_files = run_phase2_loop(
                    video_id, phase1_files, phase2_dir, 1, logger
                )
                success = len(phase2_files) > 0
                print(f"  {'✓' if success else '✗'} Phase2: {len(phase2_files)} 个结果")
            except Exception as e:
                print(f"  ✗ Phase2 失败：{e}")
                self.results["errors"].append(f"Phase2: {str(e)}")
                return False

        self.timings["phase2"] = t.duration

        # Phase 3
        print("Phase 3: 时间轴匹配")
        with Timer("phase3") as t:
            try:
                from batch.phase_runner import run_phase3_loop

                phase3_dir = os.path.join(self.output_dir, video_id, "phase3")
                phase3_results = run_phase3_loop(
                    video_id, srt_path, phase2_files, phase3_dir, logger
                )
                success = len(phase3_results) > 0
                print(
                    f"  {'✓' if success else '✗'} Phase3: {len(phase3_results)} 个有效序列"
                )
            except Exception as e:
                print(f"  ✗ Phase3 失败：{e}")
                self.results["errors"].append(f"Phase3: {str(e)}")
                return False

        self.timings["phase3"] = t.duration

        # Phase 4
        print("Phase 4: 质量评分")
        with Timer("phase4") as t:
            try:
                from batch.evaluator import evaluate_quality

                phase4_dir = os.path.join(self.output_dir, video_id, "phase4")
                os.makedirs(phase4_dir, exist_ok=True)

                scored = []
                for idx, intervals in phase3_results:
                    score = evaluate_quality(mp4_path, intervals)
                    scored.append((idx, intervals, score))

                print(f"  ✓ Phase4: {len(scored)} 个评分完成")
            except Exception as e:
                print(f"  ✗ Phase4 失败：{e}")
                self.results["errors"].append(f"Phase4: {str(e)}")
                scored = []

        self.timings["phase4"] = t.duration

        # Phase 5
        print("Phase 5: 视频生成")
        with Timer("phase5") as t:
            try:
                from make_video.step3 import cut_video_main

                phase5_dir = os.path.join(self.output_dir, video_id, "phase5")
                os.makedirs(phase5_dir, exist_ok=True)

                generated = []
                for idx, intervals, score in scored:
                    if score["total"] >= settings.BATCH_SCORE_THRESHOLD:
                        output_path = cut_video_main(
                            intervals, mp4_path, video_id, "test"
                        )
                        final_path = os.path.join(phase5_dir, f"video_{idx:03d}.mp4")
                        os.rename(output_path, final_path)
                        generated.append(final_path)
                        self.results["generated_videos"].append(
                            {"path": final_path, "score": score["total"]}
                        )

                print(f"  ✓ Phase5: 生成 {len(generated)} 个视频")
            except Exception as e:
                print(f"  ✗ Phase5 失败：{e}")
                self.results["errors"].append(f"Phase5: {str(e)}")

        self.timings["phase5"] = t.duration

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
                print(f"  ✓ 生成视频：{summary.get('videos_generated', 0)} 个")

                # 收集生成的视频信息
                for vid in summary.get("generated_videos", []):
                    self.results["generated_videos"].append(vid)
            else:
                print("  ✗ Summary 文件不存在")
                self.results["warnings"].append("Summary file not found")

            # 检查生成的视频
            gen_dir = os.path.join(multi_dir, "generated_videos")
            if os.path.exists(gen_dir):
                video_files = [f for f in os.listdir(gen_dir) if f.endswith(".mp4")]
                print(f"  ✓ 视频目录：{len(video_files)} 个文件")
        else:
            print("  ✗ 多视频输出目录不存在")
            self.results["warnings"].append("Multi-video output directory not found")

        return True

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
