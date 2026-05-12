"""Contract tests for Cursor project rule and command adaptation files."""

from __future__ import annotations

from pathlib import Path

import yaml


CURSOR_RULES = Path(".cursor/rules")
CURSOR_COMMANDS = Path(".cursor/commands")

CLAUDE_CODEX_ONLY_TERMS = (
    "CLAUDE_SKILL_DIR",
    "AskUserQuestion",
    "TaskCreate",
    "TaskUpdate",
    "TaskList",
    "request_user_input",
    "update_plan",
    "spawn_agent",
    "allowed-tools",
)


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---")
    raw = text.split("---", 2)[1]
    return yaml.safe_load(raw)


def test_cursor_rules_use_project_rule_mdc_format() -> None:
    rules = {
        CURSOR_RULES / "tide-core.mdc": "Tide HAR-driven pytest generation workflow",
        CURSOR_RULES / "tide-init.mdc": "Tide initialization workflow",
    }

    for path, description in rules.items():
        frontmatter = _frontmatter(path)
        text = path.read_text(encoding="utf-8")

        assert frontmatter["description"] == description
        assert "alwaysApply" in frontmatter
        assert frontmatter["alwaysApply"] is False
        assert "TIDE_PLUGIN_DIR" in text
        assert ".cursor/rules" not in text.split("---", 2)[2]
        for term in CLAUDE_CODEX_ONLY_TERMS:
            assert term not in text


def test_cursor_commands_define_tide_entrypoints() -> None:
    commands = {
        CURSOR_COMMANDS / "tide.md": "# tide",
        CURSOR_COMMANDS / "using-tide.md": "# using-tide",
    }

    for path, heading in commands.items():
        text = path.read_text(encoding="utf-8")

        assert text.startswith(heading)
        assert "Cursor" in text
        assert "TIDE_PLUGIN_DIR" in text
        for term in CLAUDE_CODEX_ONLY_TERMS:
            assert term not in text


def test_cursor_adapter_references_existing_tide_assets() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            CURSOR_RULES / "tide-core.mdc",
            CURSOR_RULES / "tide-init.mdc",
            CURSOR_COMMANDS / "tide.md",
            CURSOR_COMMANDS / "using-tide.md",
        ]
    )

    assert "scripts.har_parser" in combined
    assert "scripts.scenario_validator" in combined
    assert "scripts.convention_scanner" in combined
    assert "agents/scenario-analyzer.md" in combined
    assert "agents/project-scanner.md" in combined
