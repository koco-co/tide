"""Tests for test runner wrapper — TDD (write first, implement second)."""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.test_runner import (
    TestResult as PytestRunResult,
    build_pytest_command,
    parse_pytest_output,
    run_tests,
    write_execution_report,
)


class TestBuildCommand:
    def test_basic_command(self, tmp_path: Path) -> None:
        """应生成包含 pytest 和测试路径的基本命令。"""
        test_path = tmp_path / "tests"
        cmd = build_pytest_command(test_path)

        assert "pytest" in cmd
        assert str(test_path) in cmd

    def test_collect_only(self, tmp_path: Path) -> None:
        """collect_only=True 时应在命令中包含 --collect-only 参数。"""
        test_path = tmp_path / "tests"
        cmd = build_pytest_command(test_path, collect_only=True)

        assert "--collect-only" in cmd

    def test_with_allure(self, tmp_path: Path) -> None:
        """指定 allure_dir 时应在命令中包含 --alluredir= 参数。"""
        test_path = tmp_path / "tests"
        allure_dir = tmp_path / "results"
        cmd = build_pytest_command(test_path, allure_dir=allure_dir)

        assert any(arg.startswith("--alluredir=") for arg in cmd)


class TestParseOutput:
    def test_parses_passed(self) -> None:
        """应正确解析全部通过的测试结果。"""
        output = "===== 10 passed in 2.34s ====="
        result = parse_pytest_output(output, return_code=0)

        assert result.passed == 10
        assert result.failed == 0
        assert result.success is True

    def test_parses_mixed(self) -> None:
        """应正确解析混合结果（通过、失败、跳过）。"""
        output = "===== 8 passed, 2 failed, 1 skipped in 5.00s ====="
        result = parse_pytest_output(output, return_code=1)

        assert result.passed == 8
        assert result.failed == 2
        assert result.skipped == 1
        assert result.success is False

    def test_parses_no_tests(self) -> None:
        """无测试运行时 passed 应为 0。"""
        output = "===== no tests ran in 0.01s ====="
        result = parse_pytest_output(output, return_code=5)

        assert result.passed == 0


class TestRunTests:
    def test_returns_result(self, tmp_path: Path) -> None:
        """成功执行时应返回正确的 TestResult。"""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "===== 5 passed in 1.00s ====="

        with patch("scripts.test_runner.subprocess.run", return_value=mock_proc):
            result = run_tests(tmp_path / "tests")

        assert result.passed == 5
        assert result.success is True


class TestWriteExecutionReport:
    def test_overwrites_stale_counts_with_final_pytest_result(self, tmp_path: Path) -> None:
        report_path = tmp_path / "execution-report.json"
        report_path.write_text('{"passed": 17, "failed": 10}')

        result = PytestRunResult(
            passed=27,
            failed=0,
            skipped=0,
            errors=0,
            success=True,
            output="================ 27 passed in 71.45s ================",
        )
        write_execution_report(
            report_path,
            result,
            total_tests=27,
            command=["python", "-m", "pytest", "tests/generated"],
        )

        doc = json.loads(report_path.read_text())
        assert doc["overall_status"] == "PASS"
        assert doc["total_tests"] == 27
        assert doc["passed"] == 27
        assert doc["failed"] == 0
        assert doc["errors"] == 0
        assert doc["command"] == ["python", "-m", "pytest", "tests/generated"]

    def test_cli_accepts_pytest_command_with_dash_args(self, tmp_path: Path) -> None:
        report_path = tmp_path / "execution-report.json"
        output_path = tmp_path / "pytest-output.txt"
        output_path.write_text("================ 2 passed in 1.00s ================")

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.test_runner",
                "report",
                "--report",
                str(report_path),
                "--output-file",
                str(output_path),
                "--return-code",
                "0",
                "--total-tests",
                "2",
                "--command",
                "python",
                "-m",
                "pytest",
                "tests/generated",
                "-q",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc.returncode == 0, proc.stderr
        doc = json.loads(report_path.read_text())
        assert doc["passed"] == 2
        assert doc["command"] == ["python", "-m", "pytest", "tests/generated", "-q"]
