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


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def resolve_har_input(argument: str, project_root: Path) -> Path:
    """Resolve a HAR argument without guessing among multiple candidates."""
    raw = argument.strip()
    if not raw:
        raise ValueError("HAR file path is required")

    root = project_root.expanduser().resolve()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()

    if candidate.is_file():
        if candidate.suffix.lower() != ".har":
            raise ValueError(f"HAR path must end with .har: {candidate}")
        return candidate

    if candidate.is_dir():
        har_files = sorted(candidate.glob("*.har"), key=lambda p: p.name)
        if len(har_files) == 1:
            return har_files[0].resolve()
        if len(har_files) > 1:
            candidates = "\n".join(
                f"- {_display_path(path.resolve(), root)}" for path in har_files
            )
            raise ValueError(
                "Multiple HAR files found; Do not guess. Ask the user to specify one exact .har path:\n"
                f"{candidates}"
            )
        raise FileNotFoundError(f"No .har files found in directory: {candidate}")

    raise FileNotFoundError(f"HAR file not found: {candidate}")


def snapshot_har(har_path: Path, project_root: Path, session_id: str) -> HarSnapshot:
    source = resolve_har_input(str(har_path), project_root)

    dest_dir = project_root.expanduser().resolve() / ".tide" / "inputs" / session_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / source.name
    shutil.copy2(source, dest)

    return HarSnapshot(
        original_path=source,
        snapshot_path=dest,
        sha256=_sha256(dest),
    )
