"""Tests for hook system."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.claude_hooks import build_user_prompt_context, ensure_write_scope_snapshot, evaluate_write_scope
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
        assert "--quick --yes --non-interactive" in context
        assert "scripts.deterministic_case_writer" in context
        assert "do not continue with project-native enhancement" in context
        assert ".tide/final-report.md" in context
        assert "stop immediately" in context
        assert "不要自由生成" in context

    def test_user_prompt_hook_creates_write_scope_snapshot(self, tmp_path: Path) -> None:
        forbidden_dir = tmp_path / "api"
        forbidden_dir.mkdir()
        (forbidden_dir / "assets_api.py").write_text("class AssetsApi: pass\n", encoding="utf-8")

        created = ensure_write_scope_snapshot(str(tmp_path))

        snapshot = tmp_path / ".tide" / "write-scope-snapshot.json"
        assert created
        assert snapshot.exists()
        assert "api/assets_api.py" in snapshot.read_text(encoding="utf-8")
        assert not ensure_write_scope_snapshot(str(tmp_path))

    def test_user_prompt_hook_runs_from_target_cwd(self, tmp_path: Path) -> None:
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "assets_api.py").write_text("class AssetsApi: pass\n", encoding="utf-8")
        payload = {"prompt": "HAR 在 .tide/trash 下，请生成接口测试", "cwd": str(tmp_path)}

        result = subprocess.run(
            [sys.executable, str(Path("scripts/claude_hooks.py").resolve()), "user-prompt-submit"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=tmp_path,
            check=False,
        )

        assert result.returncode == 0
        assert "scripts.deterministic_case_writer" in result.stdout
        assert (tmp_path / ".tide" / "write-scope-snapshot.json").exists()

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

    def test_write_scope_blocks_direct_tide_generated_test_writes(self) -> None:
        decision = evaluate_write_scope(
            {"file_path": "/repo/testcases/scenariotest/assets/data_map/tide_generated_data_map_test.py"},
            cwd="/repo",
        )

        assert not decision.allowed
        assert "scripts.deterministic_case_writer" in decision.reason

    @pytest.mark.parametrize(
        "command",
        [
            "cat > utils/assets/requests/meta_data_requests.py <<'EOF'\npass\nEOF",
            "cp /tmp/generated.py api/assets/assets_api.py",
            "touch resource/common/msg.json",
            "python -c \"open('config/env.py', 'w').write('x')\"",
        ],
    )
    def test_write_scope_blocks_bash_writes_to_forbidden_paths(self, command: str) -> None:
        decision = evaluate_write_scope({"command": command}, cwd="/repo")

        assert not decision.allowed

    def test_write_scope_allows_bash_reads_from_forbidden_paths(self) -> None:
        decision = evaluate_write_scope(
            {"command": "rg 'SparkThrift' api utils resource"},
            cwd="/repo",
        )

        assert decision.allowed

    def test_hook_manifest_registers_prompt_and_write_scope_hooks(self) -> None:
        manifest = json.loads(Path("hooks/hooks.json").read_text(encoding="utf-8"))

        prompt_command = manifest["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        assert "scripts/claude_hooks.py" in prompt_command
        assert "user-prompt-submit" in prompt_command

        pre_tool = manifest["hooks"]["PreToolUse"][0]
        assert pre_tool["matcher"] == "Write|Edit|MultiEdit|Bash"
        pre_tool_command = pre_tool["hooks"][0]["command"]
        assert "scripts/claude_hooks.py" in pre_tool_command
        assert "pre-tool-use" in pre_tool_command
