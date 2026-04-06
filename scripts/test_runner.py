"""Pytest execution wrapper with result parsing."""
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestResult:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    success: bool = False
    output: str = ""


def build_pytest_command(
    test_path: Path,
    collect_only: bool = False,
    allure_dir: Path | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build a pytest command list for subprocess execution."""
    cmd = ["uv", "run", "pytest", str(test_path), "-v"]

    if collect_only:
        cmd.append("--collect-only")

    if allure_dir is not None:
        cmd.append(f"--alluredir={allure_dir}")

    if extra_args:
        cmd.extend(extra_args)

    return cmd


def parse_pytest_output(output: str, return_code: int) -> TestResult:
    """Parse pytest stdout into a TestResult dataclass."""
    counts: dict[str, int] = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}

    for match in re.finditer(r"(\d+) (passed|failed|skipped|error)", output):
        value = int(match.group(1))
        key = match.group(2)
        counts[key] = value

    return TestResult(
        passed=counts["passed"],
        failed=counts["failed"],
        skipped=counts["skipped"],
        errors=counts["error"],
        success=return_code == 0,
        output=output,
    )


def run_tests(
    test_path: Path,
    collect_only: bool = False,
    allure_dir: Path | None = None,
    timeout: int = 300,
) -> TestResult:
    """Execute pytest and return a parsed TestResult."""
    cmd = build_pytest_command(test_path, collect_only=collect_only, allure_dir=allure_dir)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return parse_pytest_output(proc.stdout, proc.returncode)
    except subprocess.TimeoutExpired:
        return TestResult(success=False, output="Test execution timed out")
    except Exception as e:
        return TestResult(success=False, output=str(e))
