# Iter14 Write Scope Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent Tide fresh runs from silently modifying target project business/helper code outside the allowed `.tide/` and `testcases/` write scope.

**Architecture:** Add a deterministic write-scope guard script with `snapshot` and `verify` modes. Snapshot records hashes for denied prefixes before generation; verify compares after generation and exits nonzero if forbidden files changed or appeared. Update Tide skill/agent contracts to run it around code generation and review.

**Tech Stack:** Python 3.14, pathlib/hashlib/json, pytest.

---

## File Structure

- Create `scripts/write_scope_guard.py`: snapshot and verify target file state for denied prefixes.
- Create `tests/test_write_scope_guard.py`: TDD coverage for allowed writes and forbidden writes.
- Modify `skills/tide/SKILL.md`, `codex-skills/tide/SKILL.md`, `agents/case-writer.md`, and `agents/case-reviewer.md`: require the guard before and after generation/review.

### Task 1: Write Scope Guard Script

**Files:**
- Create: `scripts/write_scope_guard.py`
- Create: `tests/test_write_scope_guard.py`

- [ ] **Step 1: Write failing tests**

Add tests that:

```python
snapshot_write_scope(project_root, snapshot_path)
(project_root / "testcases/generated_test.py").write_text("ok")
verify_write_scope(project_root, snapshot_path)  # passes

(project_root / "utils/helper.py").write_text("bad")
with pytest.raises(WriteScopeViolation):
    verify_write_scope(project_root, snapshot_path)
```

Also test that modifying an existing denied file is caught.

- [ ] **Step 2: Run red tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_write_scope_guard.py -q
```

Expected: import failure because the script does not exist.

- [ ] **Step 3: Implement minimal script**

Create functions:

- `snapshot_write_scope(project_root, snapshot_path)`
- `verify_write_scope(project_root, snapshot_path)`
- `main()` with subcommands:
  - `snapshot --project-root <path> --snapshot <path>`
  - `verify --project-root <path> --snapshot <path>`

Denied prefixes: `api`, `dao`, `utils`, `config`, `testdata`, `resource`.
Allowed prefixes: `.tide`, `testcases`.

- [ ] **Step 4: Run green tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_write_scope_guard.py -q
```

Expected: tests pass.

### Task 2: Wire Guard Into Contracts

**Files:**
- Modify: `skills/tide/SKILL.md`
- Modify: `codex-skills/tide/SKILL.md`
- Modify: `agents/case-writer.md`
- Modify: `agents/case-reviewer.md`

- [ ] **Step 1: Add pre-generation snapshot command**

Add:

```bash
PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.write_scope_guard snapshot \
  --project-root "$PROJECT_ROOT" \
  --snapshot "$PROJECT_ROOT/.tide/write-scope-snapshot.json"
```

- [ ] **Step 2: Add post-generation/review verify command**

Add:

```bash
PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.write_scope_guard verify \
  --project-root "$PROJECT_ROOT" \
  --snapshot "$PROJECT_ROOT/.tide/write-scope-snapshot.json"
```

If verification fails, stop immediately and report forbidden paths. Do not continue to pytest or final success summary.

### Task 3: Verification and Commit

- [ ] **Step 1: Run targeted tests**

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_write_scope_guard.py -q
```

- [ ] **Step 2: Run full suite**

```bash
rm -f .coverage && UV_CACHE_DIR=/private/tmp/tide-uv-cache make test
```

- [ ] **Step 3: Commit and install**

```bash
git add scripts/write_scope_guard.py tests/test_write_scope_guard.py skills/tide/SKILL.md codex-skills/tide/SKILL.md agents/case-writer.md agents/case-reviewer.md docs/superpowers/plans/2026-05-12-iter14-write-scope-guard.md
git commit -m "fix(tide): iter 14 - enforce target write scope"
git push
make install-plugin
```

## Self-Review

Spec coverage:
- Prevents writes to `api/dao/utils/config/testdata` target paths.
- Keeps `.tide/` and `testcases/` writable.
- Provides deterministic evidence through snapshot JSON and verify output.

Placeholder scan:
- No placeholders.

Type consistency:
- `WriteScopeViolation`, `snapshot_write_scope`, and `verify_write_scope` are named consistently across tests and implementation.
