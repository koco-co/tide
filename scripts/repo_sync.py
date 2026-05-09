"""用于克隆和拉取 git 仓库的同步工具函数。"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from scripts.repo_profiles import NormalizedRepoProfile


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
            repo_path.parent.mkdir(parents=True, exist_ok=True)
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


def _ensure_safe_repo_path(profile: "NormalizedRepoProfile", project_root: Path) -> None:
    repos_root = (project_root / ".tide" / "repos").resolve()
    local_path = profile.local_path.resolve()
    if profile.allow_external:
        return
    if local_path != repos_root and repos_root not in local_path.parents:
        raise ValueError(
            f"{profile.name}: local_path {local_path} is outside project .tide/repos; "
            "set allow_external_repos: true to allow it explicitly"
        )


def sync_all(profiles_path: Path, project_root: Path) -> list[RepoStatus]:
    """同步 profiles YAML 中定义的所有仓库。

    返回每个 profile 对应的 RepoStatus 列表。
    """
    from scripts.repo_profiles import load_repo_profiles

    profiles = load_repo_profiles(profiles_path, project_root)
    results: list[RepoStatus] = []

    for profile in profiles:
        _ensure_safe_repo_path(profile, project_root)
        status = sync_repo(
            profile.local_path,
            repo_url=profile.remote_url,
            branch=profile.branch,
        )
        results.append(status)

    return results


def cmd_clone(args: argparse.Namespace) -> int:
    """Clone 一个仓库到 .tide/repos/<group>/<repo>。"""
    group, repo_name = parse_repo_url(args.url)
    dest = args.root / ".tide" / "repos" / group / repo_name
    if dest.exists():
        print(f"已存在: {dest}（跳过）")
        return 0

    print(f"克隆 {args.url} → {dest}（分支: {args.branch}）")
    status = sync_repo(dest, repo_url=args.url, branch=args.branch)
    _print_status(status)
    return 0 if status.success else 1


def cmd_checkout(args: argparse.Namespace) -> int:
    """批量切换所有仓库到指定分支。"""
    profiles = load_profiles(args.profiles)
    if not profiles:
        print("无已配置的仓库（repo-profiles.yaml 为空或不存在）")
        return 0

    has_error = False
    for profile in profiles:
        repo_path = args.root / profile.get("path", "")
        branch = args.branch
        name = profile.get("name", repo_path.name)

        if not (repo_path / ".git").exists():
            print(f"⚠ {name}: 仓库不存在（跳过）")
            continue

        try:
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
            rev = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            print(f"✓ {name} → {branch}（{rev.stdout.strip()}）")
        except subprocess.CalledProcessError as exc:
            print(f"✗ {name}: {exc.stderr.strip()}")
            has_error = True

    return 1 if has_error else 0


def cmd_pull(args: argparse.Namespace) -> int:
    """批量拉取所有仓库 latest。"""
    profiles = load_profiles(args.profiles)
    if not profiles:
        print("无已配置的仓库")
        return 0

    has_error = False
    for profile in profiles:
        repo_path = args.root / profile.get("path", "")
        name = profile.get("name", repo_path.name)

        if not (repo_path / ".git").exists():
            print(f"⚠ {name}: 仓库不存在（跳过）")
            continue

        status = sync_repo(repo_path, branch=profile.get("branch", "main"))
        if status.success:
            print(f"✓ {name} → {status.head_commit}")
        else:
            print(f"✗ {name}: {status.error}")
            has_error = True

    return 1 if has_error else 0


def cmd_sync(args: argparse.Namespace) -> int:
    """同步 profiles 中所有仓库（clone 或 pull）。"""
    results = sync_all(args.profiles, args.root)
    has_error = False
    for status in results:
        _print_status(status)
        if not status.success:
            has_error = True
    return 1 if has_error else 0


def _print_status(status: RepoStatus) -> None:
    if status.success:
        print(f"✓ {status.name} → {status.head_commit}")
    else:
        print(f"✗ {status.name}: {status.error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tide 源码仓库管理工具")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="项目根目录（默认当前目录）")
    parser.add_argument(
        "--profiles",
        type=Path,
        default=Path.cwd() / ".tide" / "repos" / "repo-profiles.yaml",
        help="repo-profiles.yaml 路径（默认 .tide/repos/repo-profiles.yaml）",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # clone
    clone_p = sub.add_parser("clone", help="克隆仓库到 .tide/repos/<group>/<repo>")
    clone_p.add_argument("url", help="Git 仓库 URL")
    clone_p.add_argument("-b", "--branch", default="main", help="分支（默认 main）")
    clone_p.set_defaults(func=cmd_clone)

    # checkout
    co_p = sub.add_parser("checkout", help="批量切换所有仓库到指定分支")
    co_p.add_argument("branch", help="目标分支名")
    co_p.set_defaults(func=cmd_checkout)

    # pull
    pull_p = sub.add_parser("pull", help="批量拉取所有仓库")
    pull_p.set_defaults(func=cmd_pull)

    # sync
    sync_p = sub.add_parser("sync", help="同步 profiles 中所有仓库（clone 或 pull）")
    sync_p.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
