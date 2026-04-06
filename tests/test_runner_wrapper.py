"""Tests for test runner wrapper — TDD (write first, implement second)."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.test_runner import build_pytest_command, parse_pytest_output, run_tests


class TestBuildCommand:
    def test_basic_command(self, tmp_path: Path) -> None:
        test_path = tmp_path / "tests"
        cmd = build_pytest_command(test_path)

        assert "pytest" in cmd
        assert str(test_path) in cmd

    def test_collect_only(self, tmp_path: Path) -> None:
        test_path = tmp_path / "tests"
        cmd = build_pytest_command(test_path, collect_only=True)

        assert "--collect-only" in cmd

    def test_with_allure(self, tmp_path: Path) -> None:
        test_path = tmp_path / "tests"
        allure_dir = tmp_path / "results"
        cmd = build_pytest_command(test_path, allure_dir=allure_dir)

        assert any(arg.startswith("--alluredir=") for arg in cmd)


class TestParseOutput:
    def test_parses_passed(self) -> None:
        output = "===== 10 passed in 2.34s ====="
        result = parse_pytest_output(output, return_code=0)

        assert result.passed == 10
        assert result.failed == 0
        assert result.success is True

    def test_parses_mixed(self) -> None:
        output = "===== 8 passed, 2 failed, 1 skipped in 5.00s ====="
        result = parse_pytest_output(output, return_code=1)

        assert result.passed == 8
        assert result.failed == 2
        assert result.skipped == 1
        assert result.success is False

    def test_parses_no_tests(self) -> None:
        output = "===== no tests ran in 0.01s ====="
        result = parse_pytest_output(output, return_code=5)

        assert result.passed == 0


class TestRunTests:
    def test_returns_result(self, tmp_path: Path) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "===== 5 passed in 1.00s ====="

        with patch("scripts.test_runner.subprocess.run", return_value=mock_proc):
            result = run_tests(tmp_path / "tests")

        assert result.passed == 5
        assert result.success is True
