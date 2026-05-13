"""Repo profile loading and schema normalization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from scripts.repo_sync import parse_repo_url


class NormalizedRepoProfile(BaseModel):
    name: str
    remote_url: str = ""
    branch: str = "main"
    local_path: Path
    url_prefixes: list[str] = Field(default_factory=list)
    allow_external: bool = False


def _default_local_path(project_root: Path, remote_url: str, name: str) -> Path:
    if remote_url:
        try:
            group, repo_name = parse_repo_url(remote_url)
            return project_root / ".tide" / "repos" / group / repo_name
        except ValueError:
            pass
    return project_root / ".tide" / "repos" / name


def _as_project_path(project_root: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (project_root / candidate).resolve()


def _normalize_one(raw: dict[str, Any], project_root: Path) -> NormalizedRepoProfile:
    remote_url = raw.get("remote_url") or raw.get("url") or ""
    name = raw.get("name") or Path(remote_url).stem.removesuffix(".git")
    explicit_path = raw.get("local_path") or raw.get("path") or ""
    local_path = (
        _as_project_path(project_root, explicit_path)
        if explicit_path
        else _default_local_path(project_root, remote_url, name)
    )
    prefixes = []
    for key in ("url_prefixes", "url_aliases"):
        value = raw.get(key) or []
        if isinstance(value, str):
            prefixes.append(value)
        else:
            prefixes.extend(value)
    if raw.get("url_prefix"):
        prefixes.append(raw["url_prefix"])

    return NormalizedRepoProfile(
        name=name,
        remote_url=remote_url,
        branch=raw.get("branch") or "main",
        local_path=local_path,
        url_prefixes=sorted(set(prefixes)),
        allow_external=bool(raw.get("allow_external_repos") or raw.get("allow_external")),
    )


def load_repo_profiles(profiles_path: Path, project_root: Path) -> list[NormalizedRepoProfile]:
    if not profiles_path.exists():
        return []
    data = yaml.safe_load(profiles_path.read_text(encoding="utf-8")) or {}
    raw_profiles = data.get("profiles")
    if raw_profiles is None:
        repos = data.get("repos", [])
        raw_profiles = repos.get("profiles", []) if isinstance(repos, dict) else repos
    if not isinstance(raw_profiles, list):
        raise ValueError(f"repo profiles must be a list in {profiles_path}")
    return [_normalize_one(item, project_root.resolve()) for item in raw_profiles]
