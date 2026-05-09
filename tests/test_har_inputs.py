import json
from pathlib import Path

from scripts.har_inputs import snapshot_har


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
