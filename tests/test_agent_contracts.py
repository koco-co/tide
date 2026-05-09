"""Contract tests for agent frontmatter tool declarations."""

from pathlib import Path

import yaml


AGENTS_DIR = Path("agents")


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---")
    raw = text.split("---", 2)[1]
    return yaml.safe_load(raw)


def test_scenario_analyzer_declares_write_tool() -> None:
    data = _frontmatter(AGENTS_DIR / "scenario-analyzer.md")
    tools = {item.strip() for item in data["tools"].split(",")}

    assert "Read" in tools
    assert "Bash" in tools
    assert "Write" in tools


def test_agent_docs_do_not_request_undeclared_write() -> None:
    for path in AGENTS_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        data = _frontmatter(path)
        tools = {item.strip() for item in data.get("tools", "").split(",") if item.strip()}
        body = text.split("---", 2)[2]
        if "写出" in body or "写入" in body or ".json" in body:
            assert "Write" in tools or "Bash" in tools, path
