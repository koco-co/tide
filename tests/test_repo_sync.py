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
        profiles = load_profiles(sample_repo_profiles_path)
        assert len(profiles) == 2
        assert profiles[0]["name"] == "dt-center-assets"

    def test_returns_empty_on_missing(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.yaml"
        result = load_profiles(missing)
        assert result == []


class TestSyncRepo:
    def test_clone_new_repo(self, tmp_path: Path):
        repo_path = tmp_path / "new_repo"
        # repo_path does not have .git → should clone

        mock_result = MagicMock()
        mock_result.stdout = "abc1234\n"

        with patch("scripts.repo_sync.subprocess.run") as mock_run:
            mock_run.return_value = mock_result
            status = sync_repo(repo_path, repo_url="https://git.example.com/org/repo.git", branch="main")

        assert status.success is True
        # First call should be git clone
        first_call_args = mock_run.call_args_list[0][0][0]
        assert first_call_args[0] == "git"
        assert first_call_args[1] == "clone"

    def test_pull_existing_repo(self, tmp_path: Path):
        repo_path = tmp_path / "existing_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        mock_result = MagicMock()
        mock_result.stdout = "def5678\n"

        with patch("scripts.repo_sync.subprocess.run") as mock_run:
            mock_run.return_value = mock_result
            status = sync_repo(repo_path, branch="main")

        assert status.success is True
        # Should call fetch, checkout, pull (not clone)
        all_calls = [call[0][0] for call in mock_run.call_args_list]
        subcommands = [args[1] for args in all_calls]
        assert "fetch" in subcommands
        assert "pull" in subcommands
        assert "clone" not in subcommands


class TestSyncAll:
    def test_syncs_all_profiles(self, sample_repo_profiles_path: Path, tmp_path: Path):
        fake_status = RepoStatus(name="fake", success=True, head_commit="abc1234")

        with patch("scripts.repo_sync.sync_repo", return_value=fake_status) as mock_sync:
            results = sync_all(sample_repo_profiles_path, tmp_path)

        assert mock_sync.call_count == 2
        assert len(results) == 2
