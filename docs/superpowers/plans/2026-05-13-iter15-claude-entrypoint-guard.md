# Iter15 Claude Entrypoint Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Tide safer and easier to activate from Claude Code CLI by injecting Tide routing context for natural-language HAR requests and blocking forbidden target writes even when Claude bypasses the Tide skill text.

**Architecture:** Add plugin-level Claude Code hooks in `hooks/hooks.json`. A small Python hook module reads Claude hook JSON from stdin, adds `UserPromptSubmit` context for HAR-to-test prompts, and denies `Write`/`Edit`/`MultiEdit` operations outside `.tide/` and `testcases/` when a Tide run is likely active.

**Tech Stack:** Python 3.12, pytest, Claude Code plugin hooks, JSON hook output.

---

## File Structure

- Create `scripts/claude_hooks.py`: hook entrypoint and pure helpers for prompt detection, routing context, and write-scope decisions.
- Create `hooks/hooks.json`: Claude Code plugin hook registration using `${CLAUDE_PLUGIN_ROOT}`.
- Modify `tests/test_hooks.py`: tests for routing context, allowed writes, denied writes, and hook manifest.
- Modify `commands/tide.md`: document `/tide:tide` as the reliable plugin-prefixed CLI form.
- Modify `skills/tide/SKILL.md`: remind Claude Code that plugin-prefixed invocation is `/tide:tide`.

## Task 1: Hook Tests

**Files:**
- Modify: `tests/test_hooks.py`
- Create later: `scripts/claude_hooks.py`
- Create later: `hooks/hooks.json`

- [x] **Step 1: Write failing tests**

Add tests that import the future helper functions:

```python
from scripts.claude_hooks import build_user_prompt_context, evaluate_write_scope


def test_user_prompt_context_routes_har_generation_to_tide_command() -> None:
    context = build_user_prompt_context("HAR 在 .tide/trash 下，请生成接口测试")
    assert context is not None
    assert "/tide:tide" in context
    assert "不要自由生成" in context


def test_write_scope_allows_tide_and_testcases() -> None:
    assert evaluate_write_scope({"file_path": "/repo/.tide/parsed.json"}, cwd="/repo").allowed
    assert evaluate_write_scope({"file_path": "/repo/testcases/a_test.py"}, cwd="/repo").allowed


def test_write_scope_blocks_forbidden_target_paths() -> None:
    decision = evaluate_write_scope({"file_path": "/repo/utils/assets/requests/meta_data_requests.py"}, cwd="/repo")
    assert not decision.allowed
    assert "utils/assets/requests/meta_data_requests.py" in decision.reason
```

- [x] **Step 2: Run tests and verify failure**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_hooks.py -q
```

Expected: import failure for `scripts.claude_hooks`.

## Task 2: Hook Implementation

**Files:**
- Create: `scripts/claude_hooks.py`

- [x] **Step 1: Implement pure helper functions**

Implement:

```python
@dataclass(frozen=True)
class WriteScopeDecision:
    allowed: bool
    reason: str = ""


def build_user_prompt_context(prompt: str) -> str | None:
    ...


def evaluate_write_scope(tool_input: dict[str, Any], cwd: str) -> WriteScopeDecision:
    ...
```

Routing should trigger when prompt contains `.har` or `HAR` and generation intent such as `生成`, `接口测试`, `pytest`, or `测试`.

Denied prefixes are `api`, `dao`, `utils`, `config`, `testdata`, `resource`. Allowed prefixes are `.tide` and `testcases`.

- [x] **Step 2: Add CLI hook behavior**

`python -m scripts.claude_hooks user-prompt-submit` reads stdin JSON and prints JSON:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "..."
  }
}
```

`python -m scripts.claude_hooks pre-tool-use` reads stdin JSON and prints:

```json
{
  "decision": "block",
  "reason": "Tide write-scope violation: ..."
}
```

when a forbidden path is targeted.

- [x] **Step 3: Run targeted tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_hooks.py -q
```

Expected: pass.

## Task 3: Plugin Hook Manifest

**Files:**
- Create: `hooks/hooks.json`
- Modify: `tests/test_hooks.py`

- [x] **Step 1: Add manifest test**

Test that `hooks/hooks.json` registers:

- `UserPromptSubmit` command: `python "${CLAUDE_PLUGIN_ROOT}/scripts/claude_hooks.py" user-prompt-submit`
- `PreToolUse` matcher: `Write|Edit|MultiEdit`
- `PreToolUse` command: `python "${CLAUDE_PLUGIN_ROOT}/scripts/claude_hooks.py" pre-tool-use`

- [x] **Step 2: Create manifest**

Create `hooks/hooks.json` with those hooks and short timeouts.

- [x] **Step 3: Run targeted tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_hooks.py -q
```

Expected: pass.

## Task 4: Documentation Contract

**Files:**
- Modify: `commands/tide.md`
- Modify: `skills/tide/SKILL.md`
- Modify: `tests/test_skill_contract.py` or `tests/test_agent_contracts.py`

- [x] **Step 1: Add tests for plugin-prefixed command guidance**

Add a contract test asserting `commands/tide.md` and `skills/tide/SKILL.md` mention `/tide:tide`.

- [x] **Step 2: Update command and skill docs**

Document:

```text
In Claude Code plugin CLI/non-interactive contexts, use /tide:tide <har-file>.
```

- [x] **Step 3: Run contract tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_hooks.py tests/test_skill_contract.py -q
```

Expected: pass.

## Task 5: Full Verification and Install

**Files:**
- No code changes beyond previous tasks.

- [x] **Step 1: Run full Tide tests**

Run:

```bash
rm -f .coverage
UV_CACHE_DIR=/private/tmp/tide-uv-cache make test
```

Expected: all tests pass.

- [x] **Step 2: Install plugin**

Run:

```bash
make install-plugin
```

Expected: plugin cache updated.

- [x] **Step 3: Smoke-test hook helpers**

Run:

```bash
printf '{"prompt":"HAR 在 .tide/trash 下，请生成接口测试"}' \
  | python scripts/claude_hooks.py user-prompt-submit
```

Expected: JSON output containing `/tide:tide`.

```bash
printf '{"cwd":"/tmp/repo","tool_input":{"file_path":"/tmp/repo/utils/x.py"}}' \
  | python scripts/claude_hooks.py pre-tool-use
```

Expected: JSON output with `"decision": "block"`.

## Self-Review

- Spec coverage: addresses Iter14 blocker (`/tide` entrypoint ambiguity), natural-language HAR prompt routing, and write-scope redline.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: helper names match tests and planned implementation.
