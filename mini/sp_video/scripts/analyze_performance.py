#!/usr/bin/env python3
"""
analyze_performance.py - 性能分析工具

分析批量生成的性能数据，识别瓶颈
"""

import os
import sys
import json
import argparse
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self, log_file=None, results_dir=None):
        self.log_file = log_file
        self.results_dir = results_dir
        self.events = []
        self.phase_times = defaultdict(list)
        self.video_times = defaultdict(list)

    def load_logs(self):
        """加载日志文件"""
        if not self.log_file or not os.path.exists(self.log_file):
            print(f"警告：日志文件不存在 {self.log_file}")
            return False

        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    self.events.append(event)
                except json.JSONDecodeError:
                    continue

        print(f"加载了 {len(self.events)} 个日志事件")
        return len(self.events) > 0

    def analyze_phases(self):
        """分析各阶段性能"""
        phase_durations = defaultdict(list)

        for event in self.events:
            phase = event.get("phase")
            duration = event.get("duration_sec")
            video_id = event.get("video_id")
            status = event.get("status")

            if phase and duration:
                key = f"{video_id}_{phase}" if video_id else phase
                phase_durations[phase].append(
                    {
                        "video_id": video_id,
                        "duration": duration,
                        "status": status,
                        "iteration": event.get("iteration", 0),
                    }
                )

        return phase_durations

    def analyze_test_reports(self):
        """分析测试报告"""
        if not self.results_dir:
            return []

        reports = []
        report_dir = os.path.join(self.results_dir, "test_reports")

        if not os.path.exists(report_dir):
            return reports

        for fname in os.listdir(report_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(report_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        report = json.load(f)
                        reports.append(report)
                except (json.JSONDecodeError, IOError):
                    continue

        return sorted(reports, key=lambda x: x.get("test_date", ""), reverse=True)

    def generate_report(self, output_path=None):
        """生成分析报告"""
        phase_data = self.analyze_phases()
        test_reports = self.analyze_test_reports()

        lines = []
        lines.append("=" * 70)
        lines.append("性能分析报告")
        lines.append("=" * 70)
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"日志文件：{self.log_file}")
        lines.append("")

        # 阶段分析
        lines.append("-" * 70)
        lines.append("阶段性能分析")
        lines.append("-" * 70)

        if phase_data:
            lines.append(
                f"\n{'阶段':<15} {'次数':>8} {'平均 (s)':>12} {'最小 (s)':>12} {'最大 (s)':>12} {'总计 (s)':>12}"
            )
            lines.append("-" * 75)

            for phase in sorted(phase_data.keys()):
                durations = [e["duration"] for e in phase_data[phase]]
                count = len(durations)
                avg = sum(durations) / count if count > 0 else 0
                min_t = min(durations) if durations else 0
                max_t = max(durations) if durations else 0
                total = sum(durations)

                lines.append(
                    f"{phase:<15} {count:>8} {avg:>12.2f} {min_t:>12.2f} {max_t:>12.2f} {total:>12.2f}"
                )

        # 测试报告分析
        if test_reports:
            lines.append("")
            lines.append("-" * 70)
            lines.append("测试报告分析")
            lines.append("-" * 70)

            lines.append(f"\n找到 {len(test_reports)} 个测试报告")
            lines.append("")

            for i, report in enumerate(test_reports[:5], 1):  # 只显示最近 5 个
                lines.append(f"报告 {i}:")
                lines.append(f"  日期：{report.get('test_date', 'N/A')}")
                lines.append(f"  模式：{report.get('mode', 'N/A')}")
                lines.append(f"  状态：{report.get('status', 'N/A')}")
                lines.append(f"  总耗时：{report.get('total_duration', 0):.2f}s")

                timings = report.get("timings", {})
                if timings:
                    lines.append(f"  时间分布:")
                    total = sum(timings.values())
                    for phase, duration in sorted(
                        timings.items(), key=lambda x: x[1], reverse=True
                    ):
                        pct = (duration / total * 100) if total > 0 else 0
                        lines.append(f"    - {phase}: {duration:.2f}s ({pct:.1f}%)")

                gen_videos = report.get("generated_videos", [])
                if gen_videos:
                    lines.append(f"  生成视频：{len(gen_videos)} 个")

                errors = report.get("errors", [])
                if errors:
                    lines.append(f"  错误：{len(errors)} 个")
                    for err in errors[:3]:
                        lines.append(f"    - {err}")

                lines.append("")

        # 瓶颈分析
        lines.append("-" * 70)
        lines.append("瓶颈分析")
        lines.append("-" * 70)

        if phase_data:
            total_time = sum(
                sum(e["duration"] for e in events) for events in phase_data.values()
            )

            lines.append("\n按总耗时排序的阶段:")
            phase_totals = []
            for phase, events in phase_data.items():
                total = sum(e["duration"] for e in events)
                phase_totals.append((phase, total))

            phase_totals.sort(key=lambda x: x[1], reverse=True)

            for phase, total in phase_totals:
                pct = (total / total_time * 100) if total_time > 0 else 0
                bottleneck = "← 瓶颈" if pct > 30 else ""
                lines.append(f"  {phase}: {total:.2f}s ({pct:.1f}%) {bottleneck}")

        # 建议
        lines.append("")
        lines.append("-" * 70)
        lines.append("优化建议")
        lines.append("-" * 70)

        suggestions = []

        if phase_data:
            # 检查 Phase1/2 是否耗时过长
            phase1_total = sum(e["duration"] for e in phase_data.get("phase1", []))
            phase2_total = sum(e["duration"] for e in phase_data.get("phase2", []))

            if phase1_total > 60:
                suggestions.append("Phase1 耗时较长，考虑：")
                suggestions.append("  - 降低 BATCH_PHASE1_COUNT")
                suggestions.append("  - 优化 AI 提示词减少 token 数")
                suggestions.append("  - 使用更快的 AI 模型")

            if phase2_total > 120:
                suggestions.append("Phase2 耗时较长，考虑：")
                suggestions.append("  - 降低 BATCH_PHASE2_COUNT")
                suggestions.append("  - 简化脚本生成 prompt")

            # 检查失败率
            total_events = len(self.events)
            failed_events = sum(1 for e in self.events if e.get("status") == "failed")
            fail_rate = (failed_events / total_events * 100) if total_events > 0 else 0

            if fail_rate > 10:
                suggestions.append(f"失败率较高 ({fail_rate:.1f}%)，建议：")
                suggestions.append("  - 检查错误日志")
                suggestions.append("  - 增加重试机制")
                suggestions.append("  - 添加超时处理")

        if not suggestions:
            suggestions.append("当前性能表现良好，无明显瓶颈")

        for suggestion in suggestions:
            lines.append(f"  {suggestion}")

        # 生成视频统计
        if test_reports:
            lines.append("")
            lines.append("-" * 70)
            lines.append("生成视频统计")
            lines.append("-" * 70)

            total_generated = sum(
                len(r.get("generated_videos", [])) for r in test_reports
            )

            lines.append(f"\n总计生成视频：{total_generated} 个")

            # 按模式统计
            single_count = sum(
                len(r.get("generated_videos", []))
                for r in test_reports
                if r.get("mode") == "single"
            )
            multi_count = sum(
                len(r.get("generated_videos", []))
                for r in test_reports
                if r.get("mode") == "multi"
            )

            lines.append(f"  单视频模式：{single_count} 个")
            lines.append(f"  多视频模式：{multi_count} 个")

        report_text = "\n".join(lines)

        # 输出
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            print(f"报告已保存到：{output_path}")
        else:
            print(report_text)

        return report_text


def main():
    parser = argparse.ArgumentParser(description="性能分析工具")
    parser.add_argument("--log", default="./data/batch_log.jsonl", help="日志文件路径")
    parser.add_argument(
        "--results-dir", default="./data/batch_results", help="结果目录路径"
    )
    parser.add_argument("--output", default=None, help="输出报告路径（可选）")

    args = parser.parse_args()

    analyzer = PerformanceAnalyzer(log_file=args.log, results_dir=args.results_dir)

    if not analyzer.load_logs():
        print("无法加载日志，跳过分析")
        return

    analyzer.generate_report(output_path=args.output)


if __name__ == "__main__":
    main()
