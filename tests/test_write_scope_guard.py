"""Tests for target write-scope guard."""
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.write_scope_guard import (
    WriteScopeViolation,
    snapshot_write_scope,
    verify_write_scope,
)


def test_verify_allows_testcases_writes(tmp_path: Path) -> None:
    snapshot = tmp_path / ".tide" / "write-scope-snapshot.json"
    snapshot_write_scope(tmp_path, snapshot)

    generated = tmp_path / "testcases" / "generated_test.py"
    generated.parent.mkdir(parents=True)
    generated.write_text("def test_ok():\n    assert True\n")

    verify_write_scope(tmp_path, snapshot)


def test_verify_rejects_new_forbidden_file(tmp_path: Path) -> None:
    snapshot = tmp_path / ".tide" / "write-scope-snapshot.json"
    snapshot_write_scope(tmp_path, snapshot)

    helper = tmp_path / "utils" / "assets" / "requests" / "meta_data_requests.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("class MetaDataRequest:\n    pass\n")

    with pytest.raises(WriteScopeViolation, match="utils/assets/requests/meta_data_requests.py"):
        verify_write_scope(tmp_path, snapshot)


def test_verify_rejects_modified_forbidden_file(tmp_path: Path) -> None:
    helper = tmp_path / "utils" / "assets" / "requests" / "meta_data_requests.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("class MetaDataRequest:\n    pass\n")

    snapshot = tmp_path / ".tide" / "write-scope-snapshot.json"
    snapshot_write_scope(tmp_path, snapshot)

    helper.write_text("class MetaDataRequest:\n    def new_method(self):\n        return None\n")

    with pytest.raises(WriteScopeViolation, match="modified"):
        verify_write_scope(tmp_path, snapshot)


def test_cli_reports_violation_without_traceback(tmp_path: Path) -> None:
    helper = tmp_path / "utils" / "helper.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("before")

    snapshot = tmp_path / ".tide" / "write-scope-snapshot.json"
    snapshot_write_scope(tmp_path, snapshot)
    helper.write_text("after")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.write_scope_guard",
            "verify",
            "--project-root",
            str(tmp_path),
            "--snapshot",
            str(snapshot),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Forbidden target writes detected" in proc.stderr
    assert "Traceback" not in proc.stderr
