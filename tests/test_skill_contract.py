"""Contract tests for skills/tide/SKILL.md headless orchestration rules."""

from pathlib import Path


SKILL = Path("skills/tide/SKILL.md")


def test_skill_defines_headless_policy() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "--yes" in text
    assert "--non-interactive" in text
    assert "requires_confirmation=false" in text
    assert "不得调用 AskUserQuestion" in text


def test_skill_uses_project_root_and_plugin_dir_names() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "PROJECT_ROOT" in text
    assert "PLUGIN_DIR" in text
    assert "CLAUDE_SKILL_DIR" in text
    assert "scripts.run_context" in text


def test_skill_uses_deterministic_har_parser_cli() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "scripts.har_parser" in text
    assert ".tide/parsed.json" in text
    assert "har-parser Agent" not in text
