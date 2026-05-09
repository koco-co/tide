"""Tests for repo_sync module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.repo_sync import RepoStatus, load_profiles, parse_repo_url, sync_all, sync_repo


class TestParseRepoUrl:
    def test_https_url(self):
        result = parse_repo_url("https://git.example.com/CustomItem/dt-center-assets.git")
        assert result == ("CustomItem", "dt-center-assets")

    def test_ssh_url(self):
        result = parse_repo_url("git@git.example.com:CustomItem/dt-center-assets.git")
        assert result == ("CustomItem", "dt-center-assets")

    def test_nested_group(self):
        result = parse_repo_url("https://git.example.com/org/sub/repo.git")
        assert result == ("org/sub", "repo")

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_repo_url("not-a-url")


class TestLoadProfiles:
    def test_loads_yaml(self, sample_repo_profiles_path: Path):
        """从 YAML 文件加载 profiles 并验证条目数量和内容。"""
        profiles = load_profiles(sample_repo_profiles_path)
        assert len(profiles) == 2
        assert profiles[0]["name"] == "dt-center-assets"

    def test_returns_empty_on_missing(self, tmp_path: Path):
        """文件不存在时应返回空列表。"""
        missing = tmp_path / "nonexistent.yaml"
        result = load_profiles(missing)
        assert result == []


class TestSyncRepo:
    def test_clone_new_repo(self, tmp_path: Path):
        """repo_path 不含 .git 时应执行克隆操作。"""
        repo_path = tmp_path / "new_repo"
        # repo_path 不含 .git → 应克隆

        mock_result = MagicMock()
        mock_result.stdout = "abc1234\n"

        with patch("scripts.repo_sync.subprocess.run") as mock_run:
            mock_run.return_value = mock_result
            status = sync_repo(repo_path, repo_url="https://git.example.com/org/repo.git", branch="main")

        assert status.success is True
        # 第一次调用应为 git clone
        first_call_args = mock_run.call_args_list[0][0][0]
        assert first_call_args[0] == "git"
        assert first_call_args[1] == "clone"

    def test_pull_existing_repo(self, tmp_path: Path):
        """repo_path 已含 .git 时应执行拉取操作。"""
        repo_path = tmp_path / "existing_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        mock_result = MagicMock()
        mock_result.stdout = "def5678\n"

        with patch("scripts.repo_sync.subprocess.run") as mock_run:
            mock_run.return_value = mock_result
            status = sync_repo(repo_path, branch="main")

        assert status.success is True
        # 应调用 fetch、checkout、pull（而非 clone）
        all_calls = [call[0][0] for call in mock_run.call_args_list]
        subcommands = [args[1] for args in all_calls]
        assert "fetch" in subcommands
        assert "pull" in subcommands
        assert "clone" not in subcommands


class TestSyncAll:
    def test_syncs_all_profiles(self, sample_repo_profiles_path: Path, tmp_path: Path):
        """sync_all 应对 profiles 中的每个仓库调用一次 sync_repo。"""
        fake_status = RepoStatus(name="fake", success=True, head_commit="abc1234")

        with patch("scripts.repo_sync.sync_repo", return_value=fake_status) as mock_sync:
            results = sync_all(sample_repo_profiles_path, tmp_path)

        assert mock_sync.call_count == 2
        assert len(results) == 2


def test_sync_all_defaults_clone_path_under_tide_repos(tmp_path: Path) -> None:
    profiles = tmp_path / ".tide" / "repo-profiles.yaml"
    profiles.parent.mkdir()
    profiles.write_text(
        """
repos:
  - name: dt-center-assets
    remote_url: https://git.example.com/CustomItem/dt-center-assets.git
    branch: develop
    url_prefixes:
      - /dassets/v1/
""",
        encoding="utf-8",
    )
    mock_result = MagicMock()
    mock_result.stdout = "abc1234\n"

    with patch("scripts.repo_sync.subprocess.run") as mock_run:
        mock_run.return_value = mock_result
        results = sync_all(profiles, tmp_path)

    assert results[0].success is True
    clone_args = mock_run.call_args_list[0][0][0]
    assert str(tmp_path / ".tide" / "repos" / "CustomItem" / "dt-center-assets") in clone_args


def test_sync_all_rejects_external_path_without_allow_flag(tmp_path: Path) -> None:
    profiles = tmp_path / ".tide" / "repo-profiles.yaml"
    profiles.parent.mkdir()
    profiles.write_text(
        f"""
profiles:
  - name: external
    url: https://git.example.com/org/external.git
    path: {tmp_path.parent / "external"}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="outside project .tide/repos"):
        sync_all(profiles, tmp_path)
