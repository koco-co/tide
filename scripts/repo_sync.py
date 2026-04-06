"""Repository sync utilities for cloning and pulling git repos."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RepoStatus:
    name: str
    success: bool
    head_commit: str = ""
    error: str = ""


def parse_repo_url(url: str) -> tuple[str, str]:
    """Parse a git repo URL into (group, repo_name).

    Supports HTTPS and SSH formats. Raises ValueError if the URL cannot be parsed.
    """
    https_pattern = re.compile(r"https?://[^/]+/(.+)/([^/]+?)(?:\.git)?$")
    ssh_pattern = re.compile(r"git@[^:]+:(.+)/([^/]+?)(?:\.git)?$")

    for pattern in (https_pattern, ssh_pattern):
        match = pattern.match(url)
        if match:
            return match.group(1), match.group(2)

    raise ValueError(f"Cannot parse repo URL: {url!r}")


def load_profiles(profiles_path: Path) -> list[dict]:
    """Load repo profiles from a YAML file.

    Returns an empty list if the file does not exist.
    """
    if not profiles_path.exists():
        return []

    with profiles_path.open() as f:
        config = yaml.safe_load(f)

    return config.get("profiles", [])


def sync_repo(repo_path: Path, repo_url: str = "", branch: str = "main") -> RepoStatus:
    """Clone or pull a git repository.

    If .git exists at repo_path, performs fetch + checkout + pull.
    Otherwise, clones the repo from repo_url into repo_path.
    Returns a RepoStatus with the result.
    """
    name = repo_path.name

    try:
        if (repo_path / ".git").exists():
            subprocess.run(
                ["git", "fetch", "--all"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            subprocess.run(
                ["git", "checkout", branch],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            subprocess.run(
                ["git", "pull"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            subprocess.run(
                ["git", "clone", "-b", branch, repo_url, str(repo_path)],
                capture_output=True,
                text=True,
                check=True,
            )

        rev_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        head_commit = rev_result.stdout.strip()

        return RepoStatus(name=name, success=True, head_commit=head_commit)

    except subprocess.CalledProcessError as exc:
        return RepoStatus(name=name, success=False, error=str(exc.stderr))


def sync_all(profiles_path: Path, project_root: Path) -> list[RepoStatus]:
    """Sync all repositories defined in the profiles YAML.

    Returns a list of RepoStatus for each profile.
    """
    profiles = load_profiles(profiles_path)
    results: list[RepoStatus] = []

    for profile in profiles:
        repo_path = project_root / profile.get("path", "")
        repo_url = profile.get("url", "")
        branch = profile.get("branch", "main")
        status = sync_repo(repo_path, repo_url=repo_url, branch=branch)
        results.append(status)

    return results
