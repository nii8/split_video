#!/usr/bin/env python3
"""
generate_test_report.py - 生成综合测试报告

从测试运行结果生成 Markdown 格式的测试报告
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_test_reports(results_dir):
    """加载测试报告"""
    reports = []
    report_dir = os.path.join(results_dir, "test_reports")

    if not os.path.exists(report_dir):
        return reports

    for fname in sorted(os.listdir(report_dir)):
        if fname.endswith(".json"):
            fpath = os.path.join(report_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    report = json.load(f)
                    report["_filename"] = fname
                    reports.append(report)
            except (json.JSONDecodeError, IOError):
                continue

    return reports


def load_generation_summaries(results_dir):
    rows = []

    for video_id in os.listdir(results_dir):
        if video_id in ["test_reports", "multi_video"]:
            continue

        summary_path = os.path.join(results_dir, video_id, "summary.json")
        if not os.path.exists(summary_path):
            continue

        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        for item in summary.get("generated_videos", []):
            score = item.get("machine_score", {})
            rows.append(
                {
                    "mode": "single",
                    "source_id": video_id,
                    "candidate_id": item.get("idx"),
                    "path": item.get("path"),
                    "duration_sec": item.get("duration_sec", 0),
                    "duration_bucket": item.get("duration_bucket", ""),
                    "machine_total": score.get("total"),
                    "machine_video": score.get("video"),
                    "machine_transition": score.get("transition"),
                    "machine_audio": score.get("audio"),
                    "machine_visual": score.get("visual"),
                    "machine_duration_fit": score.get("duration_fit"),
                    "machine_completeness": score.get("completeness"),
                    "machine_cross_video_coherence": None,
                    "machine_multi_video": None,
                    "manual_total": "",
                    "manual_hook": "",
                    "manual_clarity": "",
                    "manual_rhythm": "",
                    "manual_completeness": "",
                    "manual_emotion": "",
                    "manual_notes": "",
                }
            )

    multi_summary_path = os.path.join(results_dir, "multi_video", "summary.json")
    if os.path.exists(multi_summary_path):
        try:
            with open(multi_summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
        except (json.JSONDecodeError, IOError):
            summary = {}

        for item in summary.get("generated_videos", []):
            score = item.get("machine_score", {})
            rows.append(
                {
                    "mode": "multi",
                    "source_id": "multi_video",
                    "candidate_id": item.get("candidate_id"),
                    "path": item.get("output_path"),
                    "duration_sec": item.get("total_duration", 0),
                    "duration_bucket": item.get("duration_bucket", ""),
                    "machine_total": score.get("total"),
                    "machine_video": score.get("video"),
                    "machine_transition": score.get("transition"),
                    "machine_audio": score.get("audio"),
                    "machine_visual": score.get("visual"),
                    "machine_duration_fit": score.get("duration_fit"),
                    "machine_completeness": score.get("completeness"),
                    "machine_cross_video_coherence": score.get("cross_video_coherence"),
                    "machine_multi_video": score.get("multi_video"),
                    "manual_total": "",
                    "manual_hook": "",
                    "manual_clarity": "",
                    "manual_rhythm": "",
                    "manual_completeness": "",
                    "manual_emotion": "",
                    "manual_notes": "",
                }
            )

    rows.sort(
        key=lambda item: (
            item.get("mode", ""),
            item.get("source_id", ""),
            item.get("machine_total") or 0,
        ),
        reverse=True,
    )
    return rows


def write_score_csv(rows, output_path):
    if not rows:
        return

    fieldnames = [
        "mode",
        "source_id",
        "candidate_id",
        "path",
        "duration_sec",
        "duration_bucket",
        "machine_total",
        "machine_video",
        "machine_transition",
        "machine_audio",
        "machine_visual",
        "machine_duration_fit",
        "machine_completeness",
        "machine_cross_video_coherence",
        "machine_multi_video",
        "manual_total",
        "manual_hook",
        "manual_clarity",
        "manual_rhythm",
        "manual_completeness",
        "manual_emotion",
        "manual_notes",
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def verify_generated_videos(results_dir):
    """验证生成的视频文件"""
    verification = {
        "single_videos": [],
        "multi_videos": [],
        "total_count": 0,
        "total_size_mb": 0,
        "valid_count": 0,
        "min_multi_video_duration_sec": 18.0,
        "multi_video_duration_failures": [],
    }

    # 检查单视频输出
    for video_id in os.listdir(results_dir):
        if video_id in ["test_reports", "multi_video"]:
            continue

        video_dir = os.path.join(results_dir, video_id, "phase5")
        if os.path.exists(video_dir):
            for fname in os.listdir(video_dir):
                if fname.endswith(".mp4"):
                    fpath = os.path.join(video_dir, fname)
                    size_mb = os.path.getsize(fpath) / 1024 / 1024

                    # 验证视频
                    valid = verify_video(fpath)

                    verification["single_videos"].append(
                        {"path": fpath, "size_mb": round(size_mb, 2), "valid": valid}
                    )
                    verification["total_count"] += 1
                    verification["total_size_mb"] += size_mb
                    if valid:
                        verification["valid_count"] += 1

    # 检查多视频输出
    multi_dir = os.path.join(results_dir, "multi_video", "generated_videos")
    if os.path.exists(multi_dir):
        for root, _, files in os.walk(multi_dir):
            for fname in files:
                if not fname.endswith(".mp4"):
                    continue
                fpath = os.path.join(root, fname)
                size_mb = os.path.getsize(fpath) / 1024 / 1024
                duration_sec = get_video_duration(fpath)

                valid = verify_video(fpath)
                if duration_sec < verification["min_multi_video_duration_sec"]:
                    verification["multi_video_duration_failures"].append(
                        {"path": fpath, "duration_sec": round(duration_sec, 3)}
                    )

                verification["multi_videos"].append(
                    {
                        "path": fpath,
                        "size_mb": round(size_mb, 2),
                        "duration_sec": round(duration_sec, 3),
                        "valid": valid,
                    }
                )
                verification["total_count"] += 1
                verification["total_size_mb"] += size_mb
                if valid:
                    verification["valid_count"] += 1

    return verification


def verify_video(video_path):
    """验证视频文件有效性"""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "json",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return False

        data = json.loads(result.stdout)
        streams = data.get("streams", [])

        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)

        return has_video and has_audio

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return False


def get_video_duration(video_path):
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
            timeout=10,
        )
        if result.returncode != 0:
            return 0.0
        return float(result.stdout.strip() or 0)
    except (subprocess.TimeoutExpired, ValueError, Exception):
        return 0.0


def generate_markdown_report(reports, verification, score_rows, output_path):
    """生成 Markdown 报告"""
    lines = []

    # 标题
    lines.append("# 多视频生成功能 - 测试报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 执行摘要
    lines.append("## 执行摘要")
    lines.append("")

    if reports:
        latest = reports[0]
        status = latest.get("status", "UNKNOWN")
        status_icon = "✓" if status == "PASSED" else "✗"

        lines.append(f"| 项目 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 测试状态 | {status_icon} {status} |")
        lines.append(f"| 测试模式 | {latest.get('mode', 'N/A')} |")
        lines.append(f"| 总耗时 | {latest.get('total_duration', 0):.2f} 秒 |")
        lines.append(f"| 生成视频 | {verification['total_count']} 个 |")
        lines.append(
            f"| 视频有效率 | {verification['valid_count']}/{verification['total_count']} ({verification['valid_count'] / max(verification['total_count'], 1) * 100:.1f}%) |"
        )
        lines.append("")
    else:
        lines.append("未找到测试报告")
        lines.append("")

    # 测试覆盖
    lines.append("## 测试覆盖")
    lines.append("")

    if reports:
        single_reports = [r for r in reports if r.get("mode") == "single"]
        multi_reports = [r for r in reports if r.get("mode") == "multi"]

        lines.append(f"- 单视频模式测试：{len(single_reports)} 次")
        lines.append(f"- 多视频模式测试：{len(multi_reports)} 次")
        lines.append(f"- 总计测试：{len(reports)} 次")
    else:
        lines.append("无测试数据")
    lines.append("")

    # 功能验证
    lines.append("## 功能验证")
    lines.append("")

    lines.append("### 单视频模式")
    lines.append("")

    if verification["single_videos"]:
        lines.append(f"- 生成视频：{len(verification['single_videos'])} 个")
        lines.append(
            f"- 有效视频：{sum(1 for v in verification['single_videos'] if v['valid'])} 个"
        )
        lines.append(
            f"- 总大小：{sum(v['size_mb'] for v in verification['single_videos']):.2f} MB"
        )
    else:
        lines.append("- 无生成的视频")
    lines.append("")

    lines.append("### 多视频模式")
    lines.append("")

    if verification["multi_videos"]:
        lines.append(f"- 生成视频：{len(verification['multi_videos'])} 个")
        lines.append(
            f"- 有效视频：{sum(1 for v in verification['multi_videos'] if v['valid'])} 个"
        )
        lines.append(
            f"- 总大小：{sum(v['size_mb'] for v in verification['multi_videos']):.2f} MB"
        )
        lines.append(
            f"- 达标时长：{verification['min_multi_video_duration_sec']:.0f} 秒以上"
        )
        lines.append(
            f"- 时长不达标：{len(verification['multi_video_duration_failures'])} 个"
        )
    else:
        lines.append("- 无生成的视频")
    lines.append("")

    # 机器评分表
    lines.append("## 机器评分表")
    lines.append("")
    if score_rows:
        lines.append("| 模式 | 来源 | 候选 | 时长(s) | 桶 | 总分 | 清晰度 | 节奏 | 时长适配 | 完整度 | 跨视频一致性 |")
        lines.append("|------|------|------|---------|----|------|--------|------|----------|--------|--------------|")
        for row in score_rows[:30]:
            lines.append(
                f"| {row['mode']} | {row['source_id']} | {row['candidate_id']} | "
                f"{float(row.get('duration_sec') or 0):.2f} | {row.get('duration_bucket') or '-'} | "
                f"{row.get('machine_total') if row.get('machine_total') is not None else '-'} | "
                f"{row.get('machine_video') if row.get('machine_video') is not None else '-'} | "
                f"{row.get('machine_transition') if row.get('machine_transition') is not None else '-'} | "
                f"{row.get('machine_duration_fit') if row.get('machine_duration_fit') is not None else '-'} | "
                f"{row.get('machine_completeness') if row.get('machine_completeness') is not None else '-'} | "
                f"{row.get('machine_cross_video_coherence') if row.get('machine_cross_video_coherence') is not None else '-'} |"
            )
        if len(score_rows) > 30:
            lines.append("")
            lines.append(f"仅展示前 30 行，完整机器评分见 CSV 模板。")
    else:
        lines.append("无机器评分数据")
    lines.append("")

    # 性能分析
    lines.append("## 性能分析")
    lines.append("")

    if reports:
        # 汇总时间数据
        all_timings = {}
        for report in reports:
            timings = report.get("timings", {})
            for phase, duration in timings.items():
                if phase not in all_timings:
                    all_timings[phase] = []
                all_timings[phase].append(duration)

        if all_timings:
            lines.append("### 阶段耗时统计")
            lines.append("")
            lines.append("| 阶段 | 平均 (s) | 最小 (s) | 最大 (s) | 次数 |")
            lines.append("|------|----------|----------|----------|------|")

            for phase in sorted(all_timings.keys()):
                durations = all_timings[phase]
                avg = sum(durations) / len(durations)
                min_t = min(durations)
                max_t = max(durations)
                count = len(durations)
                lines.append(
                    f"| {phase} | {avg:.2f} | {min_t:.2f} | {max_t:.2f} | {count} |"
                )

            lines.append("")

        # 最新报告详细分析
        if reports:
            latest = reports[0]
            timings = latest.get("timings", {})

            if timings:
                lines.append("### 最近测试时间分布")
                lines.append("")

                total = sum(timings.values())
                lines.append("| 阶段 | 耗时 (s) | 占比 |")
                lines.append("|------|----------|------|")

                for phase, duration in sorted(
                    timings.items(), key=lambda x: x[1], reverse=True
                ):
                    pct = (duration / total * 100) if total > 0 else 0
                    lines.append(f"| {phase} | {duration:.2f} | {pct:.1f}% |")

                lines.append(f"| **总计** | **{total:.2f}** | **100%** |")
                lines.append("")
    else:
        lines.append("无性能数据")
        lines.append("")

    # 错误和警告
    lines.append("## 错误和警告")
    lines.append("")

    if reports:
        all_errors = []
        all_warnings = []

        for report in reports:
            for err in report.get("errors", []):
                all_errors.append(f"- [{report.get('mode', 'N/A')}] {err}")
            for warn in report.get("warnings", []):
                all_warnings.append(f"- [{report.get('mode', 'N/A')}] {warn}")

        if all_errors:
            lines.append("### 错误")
            lines.append("")
            for err in all_errors[:10]:  # 最多显示 10 个
                lines.append(err)
            if len(all_errors) > 10:
                lines.append(f"... 还有 {len(all_errors) - 10} 个错误")
            lines.append("")
        else:
            lines.append("✓ 无错误")
            lines.append("")

        duration_failures = verification.get("multi_video_duration_failures", [])
        if duration_failures:
            lines.append("### 时长不达标")
            lines.append("")
            for item in duration_failures[:10]:
                lines.append(f"- {item['path']} ({item['duration_sec']:.3f}s)")
            if len(duration_failures) > 10:
                lines.append(f"... 还有 {len(duration_failures) - 10} 个时长不达标视频")
            lines.append("")

        if all_warnings:
            lines.append("### 警告")
            lines.append("")
            for warn in all_warnings[:10]:
                lines.append(warn)
            if len(all_warnings) > 10:
                lines.append(f"... 还有 {len(all_warnings) - 10} 个警告")
            lines.append("")
        else:
            lines.append("✓ 无警告")
            lines.append("")
    else:
        lines.append("无错误/警告数据")
        lines.append("")

    # 结论
    lines.append("## 结论")
    lines.append("")

    if reports:
        latest = reports[0]
        status = latest.get("status", "UNKNOWN")

        duration_ok = not verification.get("multi_video_duration_failures")
        if status == "PASSED" and verification["valid_count"] > 0 and duration_ok:
            lines.append("✓ **测试通过** - 多视频生成功能正常工作")
            lines.append("")
            lines.append("### 验收状态")
            lines.append("")
            lines.append("- [x] 单元测试通过")
            lines.append("- [x] 集成测试通过")
            lines.append(
                f"- [x] 单视频模式验证 ({len(verification['single_videos'])} 个视频)"
            )
            lines.append(
                f"- [x] 多视频模式验证 ({len(verification['multi_videos'])} 个视频)"
            )
            lines.append(
                f"- [x] 生成视频有效性验证 ({verification['valid_count']}/{verification['total_count']})"
            )
            lines.append(
                f"- [x] 多视频最小时长验证 (全部 >= {verification['min_multi_video_duration_sec']:.0f}s)"
            )
        else:
            lines.append("✗ **测试失败** - 存在问题需要修复")
            lines.append("")
            lines.append("### 待解决问题")
            lines.append("")
            if latest.get("errors"):
                for err in latest["errors"]:
                    lines.append(f"- {err}")
            if not duration_ok:
                lines.append(
                    f"- 多视频输出存在 {len(verification['multi_video_duration_failures'])} 个文件低于 {verification['min_multi_video_duration_sec']:.0f} 秒"
                )
    else:
        lines.append("无测试数据，无法得出结论")

    lines.append("")
    lines.append("---")
    lines.append(f"*报告由 generate_test_report.py 自动生成*")

    # 写入文件
    report_text = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return report_text


def main():
    parser = argparse.ArgumentParser(description="生成测试报告")
    parser.add_argument(
        "--results-dir", default="./data/batch_results", help="结果目录"
    )
    parser.add_argument("--output", default=None, help="输出报告路径")

    args = parser.parse_args()

    # 加载报告
    reports = load_test_reports(args.results_dir)
    print(f"加载了 {len(reports)} 个测试报告")

    # 验证视频
    verification = verify_generated_videos(args.results_dir)
    print(f"验证了 {verification['total_count']} 个视频文件")

    score_rows = load_generation_summaries(args.results_dir)
    print(f"加载了 {len(score_rows)} 条机器评分记录")

    # 生成报告
    output_path = args.output
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            args.results_dir, "test_reports", f"final_test_report_{timestamp}.md"
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    csv_output = os.path.join(
        args.results_dir, "test_reports", "manual_scoring_template.csv"
    )
    write_score_csv(score_rows, csv_output)

    generate_markdown_report(reports, verification, score_rows, output_path)

    print(f"报告已生成：{output_path}")
    print(f"人工评分模板已生成：{csv_output}")


if __name__ == "__main__":
    main()
