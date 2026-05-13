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


def test_skill_separates_plugin_python_from_project_test_python() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "TIDE_PY" in text
    assert "只用于运行目标项目 pytest" in text
    assert '(cd "$PLUGIN_DIR" && PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3' in text
    assert "Tide 自身脚本不得使用项目 .venv" in text


def test_skill_accepts_tide_config_repo_profiles() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "REPO_PROFILES" in text
    assert "$PROJECT_ROOT/tide-config.yaml" in text
    assert "repos.profiles" in text


def test_skill_forbids_har_base_url_as_runtime_environment() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "HAR base_url 只作为来源元数据" in text
    assert "不得把 HAR base_url 写入生成测试" in text
    assert "active environment" in text


def test_skill_requires_interactive_gates_before_generation() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "INTERACTIVE HARD GATE" in text
    assert "continue_after_parse" in text
    assert "continue_after_scenarios" in text
    assert "确认前不得进入下一阶段" in text


def test_skill_requires_final_pytest_before_success_report() -> None:
    skill_text = SKILL.read_text(encoding="utf-8")
    command_text = COMMAND.read_text(encoding="utf-8")

    for text in (skill_text, command_text):
        assert ".tide/final-pytest-output.txt" in text
        assert "没有 final-pytest-output.txt" in text
        assert "不得输出成功总结" in text
