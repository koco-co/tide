"""Pytest 执行包装器，含结果解析功能。"""
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class TestResult:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    success: bool = False
    output: str = ""


def detect_runner(project_root: Path | None = None) -> str:
    """检测项目使用的包管理器，返回 'uv' | 'poetry' | 'pip' | 'direct'。

    用于 SKILL 预检阶段，替代内联检测代码。
    """
    root = project_root or Path.cwd()

    if (root / "uv.lock").exists():
        return "uv"
    if (root / "poetry.lock").exists():
        return "poetry"
    if (root / "requirements.txt").exists():
        return "pip"
    return "direct"


def build_pytest_command(
    test_path: Path,
    collect_only: bool = False,
    allure_dir: Path | None = None,
    extra_args: list[str] | None = None,
    runner: str = "uv",  # "uv" | "pip" | "poetry" | "direct"
) -> list[str]:
    """构建用于子进程执行的 pytest 命令列表。"""
    if runner == "uv":
        cmd = ["uv", "run", "pytest"]
    elif runner == "poetry":
        cmd = ["poetry", "run", "pytest"]
    elif runner == "direct":
        cmd = [sys.executable, "-m", "pytest"]
    else:  # pip or fallback
        cmd = ["pytest"]

    cmd.extend([str(test_path), "-v"])

    if collect_only:
        cmd.append("--collect-only")

    if allure_dir is not None:
        cmd.append(f"--alluredir={allure_dir}")

    if extra_args:
        cmd.extend(extra_args)

    return cmd


def parse_pytest_output(output: str, return_code: int) -> TestResult:
    """将 pytest 标准输出解析为 TestResult 数据类。"""
    counts: dict[str, int] = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}

    for match in re.finditer(r"(\d+) (passed|failed|skipped|error|errors)", output):
        value = int(match.group(1))
        key = match.group(2)
        if key == "error":
            key = "errors"
        counts[key] = value

    return TestResult(
        passed=counts["passed"],
        failed=counts["failed"],
        skipped=counts["skipped"],
        errors=counts["errors"],
        success=return_code == 0,
        output=output,
    )


def write_execution_report(
    report_path: Path,
    result: TestResult,
    total_tests: int | None = None,
    command: list[str] | None = None,
) -> None:
    """Write execution-report.json from the final pytest result.

    This deliberately overwrites stale report counts so the JSON artifact matches
    the final command shown to the user.
    """
    computed_total = result.passed + result.failed + result.skipped + result.errors
    total = total_tests if total_tests is not None else computed_total
    status = "PASS" if result.success and result.failed == 0 and result.errors == 0 else "FAIL"
    output_lines = result.output.splitlines()

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "overall_status": status,
        "collection_success": result.success,
        "total_tests": total,
        "passed": result.passed,
        "failed": result.failed,
        "errors": result.errors,
        "skipped": result.skipped,
        "command": command or [],
        "output_tail": "\n".join(output_lines[-80:]),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def run_tests(
    test_path: Path,
    collect_only: bool = False,
    allure_dir: Path | None = None,
    timeout: int = 300,
    runner: str = "uv",  # "uv" | "pip" | "poetry" | "direct"
) -> TestResult:
    """执行 pytest 并返回解析后的 TestResult。"""
    cmd = build_pytest_command(test_path, collect_only=collect_only, allure_dir=allure_dir, runner=runner)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return parse_pytest_output(proc.stdout, proc.returncode)
    except subprocess.TimeoutExpired:
        return TestResult(success=False, output="Test execution timed out")
    except Exception as e:
        return TestResult(success=False, output=str(e))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run pytest helpers")
    sub = parser.add_subparsers(dest="subcommand")

    report_p = sub.add_parser("report")
    report_p.add_argument("--report", type=Path, required=True)
    report_p.add_argument("--output-file", type=Path, required=True)
    report_p.add_argument("--return-code", type=int, required=True)
    report_p.add_argument("--total-tests", type=int)
    report_p.add_argument("--command", dest="pytest_command", nargs=argparse.REMAINDER)

    args = parser.parse_args()
    if args.subcommand == "report":
        output = args.output_file.read_text(encoding="utf-8")
        result = parse_pytest_output(output, args.return_code)
        write_execution_report(args.report, result, total_tests=args.total_tests, command=args.pytest_command)
        print(f"Wrote execution report: {args.report}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
