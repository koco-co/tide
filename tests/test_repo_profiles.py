from pathlib import Path

from scripts.repo_profiles import load_repo_profiles


def test_loads_profiles_schema(tmp_path: Path) -> None:
    profiles = tmp_path / ".tide" / "repo-profiles.yaml"
    profiles.parent.mkdir()
    profiles.write_text(
        """
profiles:
  - name: dt-center-assets
    url: https://git.example.com/CustomItem/dt-center-assets.git
    branch: develop
    path: .tide/repos/CustomItem/dt-center-assets
    url_prefixes:
      - /api/rdos/assets/
    url_aliases:
      - /dassets/v1/
""",
        encoding="utf-8",
    )

    result = load_repo_profiles(profiles, tmp_path)

    assert result[0].name == "dt-center-assets"
    assert result[0].remote_url == "https://git.example.com/CustomItem/dt-center-assets.git"
    assert result[0].local_path == tmp_path / ".tide" / "repos" / "CustomItem" / "dt-center-assets"
    assert "/dassets/v1/" in result[0].url_prefixes


def test_loads_repos_schema_and_defaults_to_tide_repos(tmp_path: Path) -> None:
    profiles = tmp_path / ".tide" / "repo-profiles.yaml"
    profiles.parent.mkdir()
    profiles.write_text(
        """
repos:
  - name: dt-center-metadata
    remote_url: git@git.example.com:CustomItem/dt-center-metadata.git
    branch: develop
    url_prefixes:
      - /dmetadata/v1/
""",
        encoding="utf-8",
    )

    result = load_repo_profiles(profiles, tmp_path)

    assert result[0].name == "dt-center-metadata"
    assert result[0].local_path == tmp_path / ".tide" / "repos" / "CustomItem" / "dt-center-metadata"


def test_loads_tide_config_repos_profiles_schema(tmp_path: Path) -> None:
    config = tmp_path / "tide-config.yaml"
    config.write_text(
        """
project:
  name: demo
repos:
  profiles:
    - name: metadata
      remote_url: http://gitlab.example.com/group/metadata.git
      branch: release
      local_path: .tide/repos/metadata
      url_prefixes:
        - /dmetadata
""",
        encoding="utf-8",
    )

    result = load_repo_profiles(config, tmp_path)

    assert len(result) == 1
    assert result[0].name == "metadata"
    assert result[0].branch == "release"
    assert result[0].local_path == (tmp_path / ".tide" / "repos" / "metadata").resolve()
    assert result[0].url_prefixes == ["/dmetadata"]
