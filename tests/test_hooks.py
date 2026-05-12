"""Tests for hook system."""
import json
from pathlib import Path

import pytest

from scripts.claude_hooks import build_user_prompt_context, evaluate_write_scope
from scripts.hooks import HookPoint, HookRegistration, HookRegistry


class TestHookRegistry:
    """Hook registry tests."""

    def test_register_and_get(self) -> None:
        registry = HookRegistry()
        hook = HookRegistration(
            point=HookPoint.WAVE1_PARSE_AFTER,
            name="test-hook",
            command="echo test",
        )
        registry.register(hook)
        hooks = registry.get_hooks(HookPoint.WAVE1_PARSE_AFTER)
        assert len(hooks) == 1
        assert hooks[0].name == "test-hook"

    def test_empty_registry(self) -> None:
        registry = HookRegistry()
        assert not registry.has_hooks(HookPoint.WAVE1_PARSE_BEFORE)
        assert registry.get_hooks(HookPoint.WAVE1_PARSE_BEFORE) == []

    def test_multiple_hooks_same_point(self) -> None:
        registry = HookRegistry()
        for i in range(3):
            registry.register(HookRegistration(
                point=HookPoint.OUTPUT_NOTIFY,
                name=f"hook-{i}",
                command=f"cmd-{i}",
            ))
        assert len(registry.get_hooks(HookPoint.OUTPUT_NOTIFY)) == 3


class TestClaudeHooks:
    """Claude Code plugin hook tests."""

    def test_user_prompt_context_routes_har_generation_to_tide_command(self) -> None:
        context = build_user_prompt_context("HAR 在 .tide/trash 下，请生成接口测试")

        assert context is not None
        assert "/tide:tide" in context
        assert "不要自由生成" in context

    @pytest.mark.parametrize(
        "file_path",
        [
            "/repo/.tide/parsed.json",
            "/repo/testcases/scenariotest/assets/test_demo.py",
        ],
    )
    def test_write_scope_allows_tide_and_testcases(self, file_path: str) -> None:
        decision = evaluate_write_scope({"file_path": file_path}, cwd="/repo")

        assert decision.allowed
        assert decision.reason == ""

    def test_write_scope_blocks_forbidden_target_paths(self) -> None:
        decision = evaluate_write_scope(
            {"file_path": "/repo/utils/assets/requests/meta_data_requests.py"},
            cwd="/repo",
        )

        assert not decision.allowed
        assert "utils/assets/requests/meta_data_requests.py" in decision.reason

    def test_hook_manifest_registers_prompt_and_write_scope_hooks(self) -> None:
        manifest = json.loads(Path("hooks/hooks.json").read_text(encoding="utf-8"))

        prompt_command = manifest["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        assert "scripts/claude_hooks.py" in prompt_command
        assert "user-prompt-submit" in prompt_command

        pre_tool = manifest["hooks"]["PreToolUse"][0]
        assert pre_tool["matcher"] == "Write|Edit|MultiEdit"
        pre_tool_command = pre_tool["hooks"][0]["command"]
        assert "scripts/claude_hooks.py" in pre_tool_command
        assert "pre-tool-use" in pre_tool_command
