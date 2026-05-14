"""Contract tests for Codex plugin adaptation files."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


MANIFEST = Path(".codex-plugin/plugin.json")
MARKETPLACE = Path(".agents/plugins/marketplace.json")
CODEX_PLUGIN_ROOT = Path("plugins/tide")
CODEX_SKILLS = Path("codex-skills")
COMMANDS = Path("commands")
OPENAI_AGENT = Path("agents/openai.yaml")

CLAUDE_ONLY_TERMS = (
    "CLAUDE_SKILL_DIR",
    "AskUserQuestion",
    "TaskCreate",
    "TaskUpdate",
    "TaskList",
    "allowed-tools",
)


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---")
    raw = text.split("---", 2)[1]
    return yaml.safe_load(raw)


def test_codex_manifest_points_to_codex_skill_layer() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["name"] == "tide"
    assert data["version"] == "1.3.0"
    assert data["skills"] == "./codex-skills/"
    assert data["interface"]["displayName"] == "Tide"
    assert data["interface"]["category"] == "Coding"
    assert {"Interactive", "Read", "Write"}.issubset(data["interface"]["capabilities"])


def test_codex_marketplace_points_to_local_tide_plugin() -> None:
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))

    assert data["name"] == "tide"
    assert data["interface"]["displayName"] == "Tide"

    plugin = next(item for item in data["plugins"] if item["name"] == "tide")
    assert plugin["source"] == {"source": "local", "path": "./plugins/tide"}
    assert plugin["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
    assert plugin["category"] == "Coding"


def test_codex_plugin_wrapper_exposes_only_codex_runtime_assets() -> None:
    wrapper_manifest = CODEX_PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    wrapper_data = json.loads(wrapper_manifest.read_text(encoding="utf-8"))

    assert wrapper_manifest.exists()
    assert not wrapper_manifest.is_symlink()
    assert wrapper_data["name"] == "tide"
    assert wrapper_data["skills"] == "./skills/"
    assert (CODEX_PLUGIN_ROOT / "codex-skills" / "tide" / "SKILL.md").exists()
    assert (CODEX_PLUGIN_ROOT / "codex-skills" / "using-tide" / "SKILL.md").exists()
    assert (CODEX_PLUGIN_ROOT / "skills" / "tide" / "SKILL.md").resolve() == (
        CODEX_SKILLS / "tide" / "SKILL.md"
    ).resolve()
    assert (CODEX_PLUGIN_ROOT / "skills" / "using-tide" / "SKILL.md").resolve() == (
        CODEX_SKILLS / "using-tide" / "SKILL.md"
    ).resolve()
    assert (CODEX_PLUGIN_ROOT / "commands" / "tide.md").exists()
    assert (CODEX_PLUGIN_ROOT / "scripts" / "har_parser.py").exists()


def test_codex_skills_define_native_entries_without_claude_runtime_terms() -> None:
    expected = {
        CODEX_SKILLS / "tide" / "SKILL.md": "tide",
        CODEX_SKILLS / "using-tide" / "SKILL.md": "using-tide",
    }

    for path, name in expected.items():
        frontmatter = _frontmatter(path)
        text = path.read_text(encoding="utf-8")

        assert frontmatter["name"] == name
        assert frontmatter["description"]
        assert "TIDE_PLUGIN_DIR" in text
        assert "request_user_input" in text
        for term in CLAUDE_ONLY_TERMS:
            assert term not in text


def test_codex_commands_preserve_tide_slash_entrypoints() -> None:
    commands = {
        COMMANDS / "tide.md": "# /tide",
        COMMANDS / "using-tide.md": "# /using-tide",
    }

    for path, heading in commands.items():
        text = path.read_text(encoding="utf-8")
        assert text.startswith(heading)
        assert "Codex" in text
        for term in CLAUDE_ONLY_TERMS:
            assert term not in text


def test_codex_openai_agent_metadata_is_present() -> None:
    data = yaml.safe_load(OPENAI_AGENT.read_text(encoding="utf-8"))

    interface = data["interface"]
    assert interface["display_name"] == "Tide"
    assert "HAR" in interface["short_description"]
    assert "$tide" in interface["default_prompt"]
