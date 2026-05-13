"""Tests for the Live Execution Gate script."""

import json
from pathlib import Path

import pytest

from scripts.live_gate import detect_test_mode


def test_detect_live_requests_import() -> None:
    """File with requests import should be detected as LIVE."""
    tmp = Path("/tmp/test_live_gate_live.py")
    tmp.write_text(
        'import requests\nresponse = requests.get("http://example.com")\n',
        encoding="utf-8",
    )
    try:
        assert detect_test_mode([tmp]) == "LIVE"
    finally:
        tmp.unlink(missing_ok=True)


def test_detect_live_httpx() -> None:
    """File with httpx client should be detected as LIVE."""
    tmp = Path("/tmp/test_live_gate_httpx.py")
    tmp.write_text(
        'import httpx\nclient = httpx.Client()\nresponse = client.get("http://example.com")\n',
        encoding="utf-8",
    )
    try:
        assert detect_test_mode([tmp]) == "LIVE"
    finally:
        tmp.unlink(missing_ok=True)


def test_detect_live_self_req() -> None:
    """File with self.req pattern should be detected as LIVE."""
    tmp = Path("/tmp/test_live_gate_self_req.py")
    tmp.write_text(
        'response = self.req.post("/api/endpoint", json={"key": "value"})\n',
        encoding="utf-8",
    )
    try:
        assert detect_test_mode([tmp]) == "LIVE"
    finally:
        tmp.unlink(missing_ok=True)


def test_detect_live_session() -> None:
    """File with session.get/post/put/delete should be detected as LIVE."""
    tmp = Path("/tmp/test_live_gate_session.py")
    tmp.write_text(
        'response = session.get("http://example.com")\n',
        encoding="utf-8",
    )
    try:
        assert detect_test_mode([tmp]) == "LIVE"
    finally:
        tmp.unlink(missing_ok=True)


def test_detect_live_request_method() -> None:
    """File with .request() should be detected as LIVE."""
    tmp = Path("/tmp/test_live_gate_request_method.py")
    tmp.write_text(
        'response = client.request("POST", "http://example.com")\n',
        encoding="utf-8",
    )
    try:
        assert detect_test_mode([tmp]) == "LIVE"
    finally:
        tmp.unlink(missing_ok=True)


def test_detect_deterministic_contract_only() -> None:
    """File with only CONTRACTS dict and no HTTP calls should be DETERMINISTIC."""
    tmp = Path("/tmp/test_live_gate_deterministic.py")
    tmp.write_text(
        'CONTRACTS = {"case_01": {"status_code": 200, "code": 1}}\n\n'
        'class TestContracts:\n'
        '    def test_case(self):\n'
        '        contract = CONTRACTS["case_01"]\n'
        '        assert contract["status_code"] == 200\n',
        encoding="utf-8",
    )
    try:
        assert detect_test_mode([tmp]) == "DETERMINISTIC"
    finally:
        tmp.unlink(missing_ok=True)


def test_detect_deterministic_empty_file() -> None:
    """Empty or comment-only file should be DETERMINISTIC."""
    tmp = Path("/tmp/test_live_gate_empty.py")
    tmp.write_text("# just a comment\n", encoding="utf-8")
    try:
        assert detect_test_mode([tmp]) == "DETERMINISTIC"
    finally:
        tmp.unlink(missing_ok=True)


def test_write_live_gate_result(tmp_path: Path) -> None:
    """Test the full result output structure."""
    from scripts.live_gate import detect_test_mode, main as gate_main  # noqa: PLC0415
    import sys  # noqa: PLC0415

    # Create a deterministic test file in tmp_path
    test_file = tmp_path / "testcases" / "tide_generated_test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        'CONTRACTS = {"case_01": {"status_code": 200}}\n'
        'class Test:\n'
        '    def test(self):\n'
        '        assert True\n',
        encoding="utf-8",
    )

    result = detect_test_mode([test_file])
    assert result == "DETERMINISTIC"
