"""用于克隆和拉取 git 仓库的同步工具函数。"""

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
    """将 git 仓库 URL 解析为 (group, repo_name)。

    支持 HTTPS 和 SSH 格式。若 URL 无法解析则抛出 ValueError。
    """
    https_pattern = re.compile(r"https?://[^/]+/(.+)/([^/]+?)(?:\.git)?$")
    ssh_pattern = re.compile(r"git@[^:]+:(.+)/([^/]+?)(?:\.git)?$")

    for pattern in (https_pattern, ssh_pattern):
        match = pattern.match(url)
        if match:
            return match.group(1), match.group(2)

    raise ValueError(f"Cannot parse repo URL: {url!r}")


def load_profiles(profiles_path: Path) -> list[dict]:
    """从 YAML 文件中加载仓库 profiles。

    若文件不存在则返回空列表。
    """
    if not profiles_path.exists():
        return []

    with profiles_path.open() as f:
        config = yaml.safe_load(f)

    if config is None:
        return []

    profiles = config.get("profiles", [])
    if not isinstance(profiles, list):
        import sys
        print(f"[repo-sync] Warning: profiles is not a list in {profiles_path}", file=sys.stderr)
        return []

    return profiles


def sync_repo(repo_path: Path, repo_url: str = "", branch: str = "main") -> RepoStatus:
    """克隆或拉取一个 git 仓库。

    若 repo_path 下已存在 .git，则执行 fetch + checkout + pull。
    否则，从 repo_url 克隆仓库到 repo_path。
    返回包含操作结果的 RepoStatus。
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
        error_msg = str(exc.stderr).strip()
        if "did not match" in error_msg or "pathspec" in error_msg:
            try:
                branches = subprocess.run(
                    ["git", "branch", "-a"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )
                error_msg += f"\nAvailable branches:\n{branches.stdout}"
            except Exception:
                pass
        return RepoStatus(name=name, success=False, error=error_msg)


def sync_all(profiles_path: Path, project_root: Path) -> list[RepoStatus]:
    """同步 profiles YAML 中定义的所有仓库。

    返回每个 profile 对应的 RepoStatus 列表。
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
