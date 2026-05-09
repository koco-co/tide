"""Headless integration regression covering dtstack metadata sync flow."""

import shutil
from pathlib import Path

from scripts.har_inputs import snapshot_har
from scripts.har_parser import write_parsed_result
from scripts.run_context import resolve_run_context
from scripts.state_manager import init_session


FIXTURES = Path(__file__).parent / "fixtures"


def test_headless_flow_keeps_artifacts_inside_project(tmp_path: Path) -> None:
    project = tmp_path / "dtstack-httprunner"
    plugin = tmp_path / "tide"
    project.mkdir()
    plugin.mkdir()
    (project / ".tide").mkdir()
    shutil.copy2(FIXTURES / "dtstack_repo_profiles.yaml", project / ".tide" / "repo-profiles.yaml")
    har = FIXTURES / "dtstack_metadata_sync.har"

    ctx = resolve_run_context(f"{har} --quick --yes", project, plugin)
    state = init_session(ctx.project_root, str(ctx.har_path), metadata={"headless": True})
    snapshot = snapshot_har(ctx.har_path, ctx.project_root, state.session_id)
    parsed = write_parsed_result(
        snapshot.snapshot_path,
        ctx.project_root / ".tide" / "repo-profiles.yaml",
        ctx.project_root / ".tide" / "parsed.json",
    )

    assert har.exists()
    assert snapshot.snapshot_path.is_file()
    assert (project / ".tide" / "parsed.json").is_file()
    assert {ep.matched_repo for ep in parsed.endpoints} == {"dt-center-assets", "dt-center-metadata"}
    assert not (plugin / ".tide").exists()
