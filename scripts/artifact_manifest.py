"""Artifact manifest helpers for Tide runs."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_to_project(project_root: Path, artifact_path: Path) -> str:
    root = project_root.resolve()
    artifact = artifact_path.resolve()
    if artifact != root and root not in artifact.parents:
        raise ValueError(f"{artifact} is outside project root {root}")
    return artifact.relative_to(root).as_posix()


def collect_artifact(project_root: Path, artifact_path: Path, kind: str) -> dict[str, Any]:
    return {
        "path": _relative_to_project(project_root, artifact_path),
        "kind": kind,
        "sha256": _sha256(artifact_path),
        "size_bytes": artifact_path.stat().st_size,
    }


def write_manifest(project_root: Path, artifacts: list[dict[str, Any]]) -> Path:
    manifest_path = project_root / ".tide" / "artifact-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "artifacts": artifacts,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path
