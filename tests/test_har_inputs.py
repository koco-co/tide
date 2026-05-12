import json
from pathlib import Path

import pytest

from scripts.har_inputs import resolve_har_input, snapshot_har


def test_snapshot_har_copies_input_and_keeps_original(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    har = tmp_path / "capture.har"
    har.write_text(json.dumps({"log": {"entries": []}}))

    snapshot = snapshot_har(har, project_root, session_id="af_test")

    assert har.exists()
    assert snapshot.snapshot_path.exists()
    assert snapshot.snapshot_path == project_root / ".tide" / "inputs" / "af_test" / "capture.har"
    assert snapshot.original_path == har.resolve()
    assert len(snapshot.sha256) == 64


def test_resolve_har_input_keeps_explicit_file(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    har = tmp_path / "capture.har"
    har.write_text(json.dumps({"log": {"entries": []}}))

    resolved = resolve_har_input(str(har), project_root)

    assert resolved == har.resolve()


def test_resolve_har_input_fails_when_trash_has_multiple_hars(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    trash = project_root / ".tide" / "trash"
    trash.mkdir(parents=True)
    first = trash / "20260509_152002_172.16.122.52.har"
    second = trash / "batch_orchestration_rules.har"
    first.write_text(json.dumps({"log": {"entries": []}}))
    second.write_text(json.dumps({"log": {"entries": []}}))

    with pytest.raises(ValueError) as exc:
        resolve_har_input(".tide/trash", project_root)

    message = str(exc.value)
    assert "Multiple HAR files found" in message
    assert "20260509_152002_172.16.122.52.har" in message
    assert "batch_orchestration_rules.har" in message
    assert "Do not guess" in message
