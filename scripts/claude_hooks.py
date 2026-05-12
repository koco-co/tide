"""Claude Code plugin hooks for Tide routing and target write-scope safety."""

from __future__ import annotations

import json
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_HAR_MARKERS = ("har", ".har", "HAR")
_GENERATION_MARKERS = ("生成", "接口测试", "pytest", "测试", "generate")
_DENIED_PREFIXES = frozenset({"api", "dao", "utils", "config", "testdata", "resource"})
_SHELL_SEPARATORS = frozenset({";", "&&", "||", "|"})


@dataclass(frozen=True)
class WriteScopeDecision:
    """Decision for a candidate Claude write path."""

    allowed: bool
    reason: str = ""


def _as_project_relative(file_path: str, cwd: str) -> Path | None:
    candidate = Path(file_path).expanduser()
    root = Path(cwd).expanduser().resolve()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        return candidate.resolve().relative_to(root)
    except ValueError:
        return None


def _decision_for_path(file_path: str, cwd: str) -> WriteScopeDecision:
    rel_path = _as_project_relative(file_path, cwd)
    if rel_path is None or not rel_path.parts:
        return WriteScopeDecision(allowed=True)

    top_level = rel_path.parts[0]
    if top_level in _DENIED_PREFIXES:
        return WriteScopeDecision(
            allowed=False,
            reason=f"Tide write-scope violation: {rel_path.as_posix()} is outside .tide/ and testcases/",
        )

    return WriteScopeDecision(allowed=True)


def _shell_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command.replace("\n", " "), posix=True)
    except ValueError:
        return command.replace("\n", " ").split()


def _first_denied_bash_write(command: str, cwd: str) -> WriteScopeDecision:
    for match in re.finditer(r"(?:^|[\s])>>?\s*['\"]?([^'\"\s;]+)", command):
        decision = _decision_for_path(match.group(1), cwd)
        if not decision.allowed:
            return decision

    for match in re.finditer(
        r"open\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"][wa+]",
        command,
    ):
        decision = _decision_for_path(match.group(1), cwd)
        if not decision.allowed:
            return decision

    tokens = _shell_tokens(command)
    for index, token in enumerate(tokens):
        if token in {"touch", "mkdir", "rm"}:
            for candidate in _command_operands(tokens, index + 1):
                decision = _decision_for_path(candidate, cwd)
                if not decision.allowed:
                    return decision

        if token in {"cp", "mv"}:
            operands = list(_command_operands(tokens, index + 1))
            if operands:
                decision = _decision_for_path(operands[-1], cwd)
                if not decision.allowed:
                    return decision

        if token == "tee":
            for candidate in _command_operands(tokens, index + 1):
                decision = _decision_for_path(candidate, cwd)
                if not decision.allowed:
                    return decision

    return WriteScopeDecision(allowed=True)


def _command_operands(tokens: list[str], start: int) -> list[str]:
    operands: list[str] = []
    for token in tokens[start:]:
        if token in _SHELL_SEPARATORS:
            break
        if token.startswith("-"):
            continue
        operands.append(token)
    return operands


def build_user_prompt_context(prompt: str) -> str | None:
    """Return extra Claude context for natural-language Tide HAR generation requests."""

    if not prompt:
        return None

    has_har = any(marker in prompt for marker in _HAR_MARKERS)
    has_generation_intent = any(marker in prompt for marker in _GENERATION_MARKERS)
    if not (has_har and has_generation_intent):
        return None

    return (
        "Tide hook detected a HAR-to-interface-test generation request. "
        "Use the Claude Code SlashCommand tool to invoke `/tide:tide` for this request; "
        "in plugin CLI/non-interactive contexts the reliable command form is "
        "`/tide:tide <har-file-or-directory> --yes --non-interactive`. "
        "不要自由生成测试文件；必须执行 Tide workflow，先创建 `.tide/run-context.json` 和 "
        "`.tide/write-scope-snapshot.json`，再解析 HAR、生成场景、写测试、运行校验。"
        "Target writes are limited to `.tide/` and `testcases/`; do not modify "
        "`api/`, `dao/`, `utils/`, `config/`, `testdata/`, or `resource/`."
    )


def evaluate_write_scope(tool_input: dict[str, Any], cwd: str) -> WriteScopeDecision:
    """Evaluate whether a Claude write target is allowed for a Tide run."""

    raw_path = tool_input.get("file_path") or tool_input.get("path")
    if isinstance(raw_path, str) and raw_path.strip():
        return _decision_for_path(raw_path, cwd)

    command = tool_input.get("command")
    if isinstance(command, str) and command.strip():
        return _first_denied_bash_write(command, cwd)

    return WriteScopeDecision(allowed=True)


def _tide_guard_active(cwd: str) -> bool:
    tide_dir = Path(cwd).expanduser().resolve() / ".tide"
    return any(
        (tide_dir / marker).exists()
        for marker in (
            "run-context.json",
            "write-scope-snapshot.json",
            "parsed.json",
            "scenarios.json",
        )
    )


def _read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def user_prompt_submit() -> int:
    payload = _read_stdin_json()
    context = build_user_prompt_context(str(payload.get("prompt", "")))
    if context:
        _emit({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            },
            "suppressOutput": True,
        })
    return 0


def pre_tool_use() -> int:
    payload = _read_stdin_json()
    cwd = str(payload.get("cwd") or Path.cwd())
    if not _tide_guard_active(cwd):
        return 0

    decision = evaluate_write_scope(payload.get("tool_input", {}), cwd=cwd)
    if not decision.allowed:
        _emit({"decision": "block", "reason": decision.reason})
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: claude_hooks.py {user-prompt-submit|pre-tool-use}", file=sys.stderr)
        return 2

    command = args[0]
    if command == "user-prompt-submit":
        return user_prompt_submit()
    if command == "pre-tool-use":
        return pre_tool_use()

    print(f"unknown hook command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
