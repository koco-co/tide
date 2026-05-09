"""HAR input snapshot management."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HarSnapshot:
    original_path: Path
    snapshot_path: Path
    sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_har(har_path: Path, project_root: Path, session_id: str) -> HarSnapshot:
    source = har_path.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"HAR file not found: {source}")

    dest_dir = project_root.expanduser().resolve() / ".tide" / "inputs" / session_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / source.name
    shutil.copy2(source, dest)

    return HarSnapshot(
        original_path=source,
        snapshot_path=dest,
        sha256=_sha256(dest),
    )
