"""Contract tests for skills/tide/SKILL.md headless orchestration rules."""

from pathlib import Path


SKILL = Path("skills/tide/SKILL.md")
COMMAND = Path("commands/tide.md")


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


def test_claude_plugin_docs_include_namespaced_tide_command() -> None:
    skill_text = SKILL.read_text(encoding="utf-8")
    command_text = COMMAND.read_text(encoding="utf-8")

    assert "/tide:tide" in skill_text
    assert "/tide:tide" in command_text


def test_claude_plugin_docs_include_deterministic_fallback_steps() -> None:
    skill_text = SKILL.read_text(encoding="utf-8")
    command_text = COMMAND.read_text(encoding="utf-8")

    for text in (skill_text, command_text):
        assert "scripts.scenario_normalizer" in text
        assert "scripts.deterministic_case_writer" in text


def test_claude_plugin_docs_require_generated_assertion_gate() -> None:
    skill_text = SKILL.read_text(encoding="utf-8")
    command_text = COMMAND.read_text(encoding="utf-8")

    for text in (skill_text, command_text):
        assert "scripts.generated_assertion_gate" in text
        assert "empty L4" in text
        assert "final-report.md" in text
