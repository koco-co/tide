"""Tests for format checker rules."""
from pathlib import Path

from scripts.format_checker import check_file


class TestFormatChecker:
    """Format checker rule tests."""

    def test_clean_file_passes(self, tmp_path: Path) -> None:
        clean = tmp_path / "test_clean.py"
        clean.write_text(
            '"""Clean test."""\n\n\nclass TestClean:\n'
            '    """Clean."""\n\n'
            "    def test_ok(self) -> None:\n"
            '        assert True, "should be True"\n'
        )
        violations = check_file(str(clean))
        assert len(violations) == 0

    def test_detects_print(self, tmp_path: Path) -> None:
        bad = tmp_path / "test_bad.py"
        bad.write_text('def test_bad():\n    print("debug")\n    assert True\n')
        violations = check_file(str(bad))
        assert any(v.rule.id == "FC08" for v in violations)

    def test_detects_long_lines(self, tmp_path: Path) -> None:
        bad = tmp_path / "test_long.py"
        bad.write_text(f'x = "{" " * 130}"\n')
        violations = check_file(str(bad))
        assert any(v.rule.id == "FC09" for v in violations)

    def test_detects_missing_docstring(self, tmp_path: Path) -> None:
        bad = tmp_path / "test_no_doc.py"
        bad.write_text("class TestNoDoc:\n    def test_x(self):\n        pass\n")
        violations = check_file(str(bad))
        assert any(v.rule.id == "FC07" for v in violations)

    def test_nonexistent_file(self) -> None:
        violations = check_file("/tmp/nonexistent.py")
        assert violations == []

    def test_syntax_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "test_syntax.py"
        bad.write_text("def broken(\n")
        violations = check_file(str(bad))
        assert any(v.rule.id == "FC00" for v in violations)
