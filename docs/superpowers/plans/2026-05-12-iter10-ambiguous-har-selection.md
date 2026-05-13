# Iter10 Ambiguous HAR Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent Tide from silently selecting the wrong HAR when `.tide/trash` contains multiple `.har` files and the user did not name the intended file.

**Architecture:** Add a small deterministic resolver in `scripts/har_inputs.py` that can resolve explicit HAR paths, discover trash candidates, and fail loudly on ambiguous directory/natural-language inputs. Update the Tide skill prompt so Claude Code must call this resolver before parsing and must ask the user, or abort in non-interactive mode, instead of guessing by mtime.

**Tech Stack:** Python `pathlib`, pytest, Claude Code skill markdown.

---

### Task 1: Add Resolver Tests

**Files:**
- Modify: `tests/test_har_inputs.py`

- [ ] **Step 1: Write failing tests**

```python
def test_resolve_har_input_keeps_explicit_file(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    har = tmp_path / "capture.har"
    har.write_text(json.dumps({"log": {"entries": []}}))

    resolved = resolve_har_input(str(har), project_root)

    assert resolved == har.resolve()


def test_resolve_har_input_fails_when_trash_has_multiple_hars(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    trash = project_root / ".tide" / "trash"
    trash.mkdir(parents=True)
    first = trash / "20260509_152002_172.16.122.52.har"
    second = trash / "batch_orchestration_rules.har"
    first.write_text(json.dumps({"log": {"entries": []}}))
    second.write_text(json.dumps({"log": {"entries": []}}))

    with pytest.raises(ValueError) as exc:
        resolve_har_input(".tide/trash", project_root)

    message = str(exc.value)
    assert "Multiple HAR files found" in message
    assert "20260509_152002_172.16.122.52.har" in message
    assert "batch_orchestration_rules.har" in message
    assert "Do not guess" in message
```

- [ ] **Step 2: Run red test**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_har_inputs.py -v --tb=short
```

Expected: import or attribute failure because `resolve_har_input` does not exist yet.

### Task 2: Implement Resolver

**Files:**
- Modify: `scripts/har_inputs.py`
- Test: `tests/test_har_inputs.py`

- [ ] **Step 1: Add resolver**

```python
def resolve_har_input(argument: str, project_root: Path) -> Path:
    raw = argument.strip()
    if not raw:
        raise ValueError("HAR file path is required")

    root = project_root.expanduser().resolve()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()

    if candidate.is_file():
        if candidate.suffix.lower() != ".har":
            raise ValueError(f"HAR path must end with .har: {candidate}")
        return candidate

    if candidate.is_dir():
        har_files = sorted(candidate.glob("*.har"), key=lambda p: p.name)
        if len(har_files) == 1:
            return har_files[0].resolve()
        if len(har_files) > 1:
            rels = [str(p.resolve().relative_to(root)) if p.resolve().is_relative_to(root) else str(p.resolve()) for p in har_files]
            joined = "\n".join(f"- {rel}" for rel in rels)
            raise ValueError(
                "Multiple HAR files found; Do not guess. Ask the user to specify one exact .har path:\n"
                f"{joined}"
            )
        raise FileNotFoundError(f"No .har files found in directory: {candidate}")

    raise FileNotFoundError(f"HAR file not found: {candidate}")
```

- [ ] **Step 2: Use resolver in snapshot**

Change `snapshot_har()` to call `resolve_har_input(str(har_path), project_root)` before copying.

- [ ] **Step 3: Run green tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_har_inputs.py -v --tb=short
```

Expected: all `test_har_inputs.py` tests pass.

### Task 3: Update Tide Skill Instructions

**Files:**
- Modify: `skills/tide/SKILL.md`
- Modify: `codex-skills/tide/SKILL.md`

- [ ] **Step 1: Add no-guess policy**

Add to precheck:

```markdown
**HAR 选择不得猜测**：如果用户只说 “HAR 在 .tide/trash 下” 或传入目录路径，必须先运行 `scripts.har_inputs.resolve_har_input`。当目录中有多个 `.har` 文件时，不得按 mtime、文件大小、或模型推断自动选择。交互模式用 AskUserQuestion 列出候选文件请用户选择；无头/非交互模式必须失败并输出候选清单和示例命令，例如 `/tide .tide/trash/<exact-file>.har --yes --non-interactive`。
```

- [ ] **Step 2: Add deterministic command**

Add a command snippet that writes the resolved path to `.tide/run-context.json` before validation:

```bash
PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 - <<'PY'
import os
from pathlib import Path
from scripts.har_inputs import resolve_har_input

project_root = Path(os.environ["PROJECT_ROOT"])
har_arg = os.environ["HAR_PATH"]
print(resolve_har_input(har_arg, project_root))
PY
```

### Task 4: Verify Full Tide Suite

**Files:**
- Test: `tests/`

- [ ] **Step 1: Run targeted tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_har_inputs.py tests/test_run_context.py -v --tb=short
```

Expected: all targeted tests pass.

- [ ] **Step 2: Run full tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache make test
```

Expected: `159+ passed`, exit code 0.

### Self-Review

- Spec coverage: covers the Iter10 wrong-HAR failure by adding deterministic ambiguity detection and prompting/abort instructions.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: `resolve_har_input(argument: str, project_root: Path) -> Path` is used consistently in tests and implementation.
