from pathlib import Path

from scripts.run_context import parse_tide_arguments, resolve_run_context


def test_quick_disables_confirmations(tmp_path: Path) -> None:
    har = tmp_path / "capture.har"
    har.write_text('{"log":{"entries":[]}}')

    args = parse_tide_arguments(f"{har} --quick")

    assert args.har_path == har
    assert args.quick is True
    assert args.requires_confirmation is False


def test_yes_and_non_interactive_disable_confirmations(tmp_path: Path) -> None:
    har = tmp_path / "capture.har"
    har.write_text('{"log":{"entries":[]}}')

    yes_args = parse_tide_arguments(f"{har} --yes")
    headless_args = parse_tide_arguments(f"{har} --non-interactive")

    assert yes_args.requires_confirmation is False
    assert headless_args.requires_confirmation is False


def test_resolve_run_context_separates_project_and_plugin(tmp_path: Path) -> None:
    project_root = tmp_path / "target-project"
    plugin_dir = tmp_path / "tide-plugin"
    har = tmp_path / "capture.har"
    project_root.mkdir()
    plugin_dir.mkdir()
    har.write_text('{"log":{"entries":[]}}')

    ctx = resolve_run_context(
        argument_text=f"{har} --quick",
        project_root=project_root,
        plugin_dir=plugin_dir,
    )

    assert ctx.project_root == project_root.resolve()
    assert ctx.plugin_dir == plugin_dir.resolve()
    assert ctx.tide_dir == project_root.resolve() / ".tide"
    assert not str(ctx.tide_dir).startswith(str(plugin_dir.resolve()))
