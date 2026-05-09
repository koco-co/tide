"""Tests for artifact_manifest module."""

from pathlib import Path

import pytest

from scripts.artifact_manifest import collect_artifact, write_manifest


def test_collect_artifact_records_relative_path_and_sha256(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    artifact = project / ".tide" / "parsed.json"
    artifact.parent.mkdir()
    artifact.write_text('{"ok":true}', encoding="utf-8")

    item = collect_artifact(project, artifact, kind="parsed")

    assert item["path"] == ".tide/parsed.json"
    assert item["kind"] == "parsed"
    assert len(item["sha256"]) == 64


def test_collect_artifact_rejects_outside_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside.json"
    project.mkdir()
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="outside project root"):
        collect_artifact(project, outside, kind="bad")


def test_write_manifest(tmp_path: Path) -> None:
    project = tmp_path / "project"
    artifact = project / ".tide" / "parsed.json"
    project.mkdir()
    artifact.parent.mkdir()
    artifact.write_text("{}", encoding="utf-8")

    manifest_path = write_manifest(project, [collect_artifact(project, artifact, "parsed")])

    assert manifest_path == project / ".tide" / "artifact-manifest.json"
    assert manifest_path.exists()
