#!/usr/bin/env python3
"""
run_all_tests.sh - 运行所有测试的便捷脚本

一键运行：
1. 单元测试
2. 单视频模式集成测试
3. 多视频模式集成测试
4. 性能分析
5. 生成测试报告
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime

# Get script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)


def run_command(cmd, description):
    """运行命令"""
    print()
    print("=" * 70)
    print(f"{description}")
    print("=" * 70)
    print(f"命令：{' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=PROJECT_DIR)

    if result.returncode != 0:
        print(f"\n⚠ 命令执行失败 (退出码：{result.returncode})")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="运行所有测试")
    parser.add_argument("--skip-unit", action="store_true", help="跳过单元测试")
    parser.add_argument("--skip-single", action="store_true", help="跳过单视频模式测试")
    parser.add_argument("--skip-multi", action="store_true", help="跳过多视频模式测试")
    parser.add_argument("--video-ids", nargs="+", default=[], help="指定测试视频 ID")
    parser.add_argument("--output-report", action="store_true", help="生成最终测试报告")

    args = parser.parse_args()

    print("=" * 70)
    print("多视频生成功能 - 完整测试套件")
    print("=" * 70)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目目录：{PROJECT_DIR}")

    results = {
        "unit": True,
        "single": True,
        "multi": True,
        "performance": True,
        "report": True,
    }

    # 1. 单元测试
    if not args.skip_unit:
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_multi_video_builder.py",
            "tests/test_batch_generator.py",
            "-v",
            "--tb=short",
        ]
        results["unit"] = run_command(cmd, "1. 单元测试")
    else:
        print("\n⊘ 跳过单元测试")

    # 2. 单视频模式测试
    if not args.skip_single:
        cmd = [sys.executable, "scripts/run_comprehensive_test.py", "--mode", "single"]
        if args.video_ids:
            cmd.extend(["--videos"] + args.video_ids)
        results["single"] = run_command(cmd, "2. 单视频模式测试")
    else:
        print("\n⊘ 跳过单视频模式测试")

    # 3. 多视频模式测试
    if not args.skip_multi:
        cmd = [sys.executable, "scripts/run_comprehensive_test.py", "--mode", "multi"]
        if args.video_ids:
            cmd.extend(["--videos"] + args.video_ids)
        results["multi"] = run_command(cmd, "3. 多视频模式测试")
    else:
        print("\n⊘ 跳过多视频模式测试")

    # 4. 性能分析
    cmd = [
        sys.executable,
        "scripts/analyze_performance.py",
        "--log",
        "data/batch_log.jsonl",
        "--results-dir",
        "data/batch_results",
        "--output",
        "data/batch_results/test_reports/performance_analysis.md",
    ]
    results["performance"] = run_command(cmd, "4. 性能分析")

    # 5. 生成测试报告
    if args.output_report:
        cmd = [
            sys.executable,
            "scripts/generate_test_report.py",
            "--results-dir",
            "data/batch_results",
            "--output",
            "data/batch_results/test_reports/final_test_report.md",
        ]
        results["report"] = run_command(cmd, "5. 生成测试报告")
    else:
        print("\n⊘ 跳过最终报告生成")

    # 汇总
    print()
    print("=" * 70)
    print("测试汇总")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        icon = "✓" if result else "✗"
        print(f"  {icon} {test_name}")

    print()
    print(f"总计：{passed}/{total} 通过")
    print(f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if passed == total:
        print()
        print("✓ 所有测试通过!")
        return 0
    else:
        print()
        print(f"✗ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
