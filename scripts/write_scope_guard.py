"""Guard target-project writes to Tide-owned output paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DENIED_PREFIXES = ("api", "dao", "utils", "config", "testdata", "resource")
IGNORED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}


class WriteScopeViolation(RuntimeError):
    """Raised when generated output touched a forbidden target path."""


@dataclass(frozen=True)
class FileState:
    sha256: str
    size: int

    def to_json(self) -> dict[str, Any]:
        return {"sha256": self.sha256, "size": self.size}


def _relative_posix(project_root: Path, path: Path) -> str:
    return path.relative_to(project_root).as_posix()


def _is_denied(relpath: str) -> bool:
    first = relpath.split("/", 1)[0]
    return first in DENIED_PREFIXES


def _iter_denied_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    for prefix in DENIED_PREFIXES:
        root = project_root / prefix
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if any(part in IGNORED_DIRS for part in path.relative_to(project_root).parts):
                continue
            if path.is_file():
                files.append(path)
    return sorted(files)


def _hash_file(path: Path) -> FileState:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return FileState(sha256=digest.hexdigest(), size=path.stat().st_size)


def snapshot_write_scope(project_root: Path, snapshot_path: Path) -> dict[str, Any]:
    """Record current forbidden-path file states."""
    root = project_root.resolve()
    files = {
        _relative_posix(root, path.resolve()): _hash_file(path).to_json()
        for path in _iter_denied_files(root)
    }
    snapshot = {
        "project_root": str(root),
        "denied_prefixes": list(DENIED_PREFIXES),
        "files": files,
    }
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


def _load_snapshot(snapshot_path: Path) -> dict[str, Any]:
    if not snapshot_path.exists():
        raise FileNotFoundError(snapshot_path)
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def verify_write_scope(project_root: Path, snapshot_path: Path) -> dict[str, Any]:
    """Verify forbidden target paths are unchanged since snapshot."""
    root = project_root.resolve()
    snapshot = _load_snapshot(snapshot_path)
    before: dict[str, dict[str, Any]] = snapshot.get("files", {})
    after = {
        _relative_posix(root, path.resolve()): _hash_file(path).to_json()
        for path in _iter_denied_files(root)
    }

    added = sorted(path for path in after if path not in before and _is_denied(path))
    removed = sorted(path for path in before if path not in after and _is_denied(path))
    modified = sorted(
        path for path in after
        if path in before and after[path] != before[path] and _is_denied(path)
    )

    violations = {
        "added": added,
        "removed": removed,
        "modified": modified,
    }
    if added or removed or modified:
        detail = "; ".join(
            f"{kind}: {', '.join(paths)}"
            for kind, paths in violations.items()
            if paths
        )
        raise WriteScopeViolation(f"Forbidden target writes detected: {detail}")

    return {"ok": True, "checked_files": len(after), "violations": violations}


def main() -> None:
    parser = argparse.ArgumentParser(description="Guard Tide target write scope")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("snapshot", "verify"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--project-root", type=Path, required=True)
        cmd.add_argument("--snapshot", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            result = snapshot_write_scope(args.project_root, args.snapshot)
        else:
            result = verify_write_scope(args.project_root, args.snapshot)
    except WriteScopeViolation as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
