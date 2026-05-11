# Tide Iteration 1 Fix Plan

> **Goal:** Fix the 4 PYTHONPATH issues in SKILL.md + case-writer style convention to eliminate ModuleNotFoundError crashes and match DTStack project conventions.

## Task 1: Fix SKILL.md PYTHONPATH — run-context.json

**Objective:** Add `PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH"` to the `uv run python3` command that imports `from scripts.run_context import resolve_run_context`

**File:** `skills/tide/SKILL.md` lines 46-69

**Change:**
```
Before:
  uv run python3 - <<'PY' > "$PROJECT_ROOT/.tide/run-context.json"

After:
  PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 - <<'PY' > "$PROJECT_ROOT/.tide/run-context.json"
```

## Task 2: Fix SKILL.md PYTHONPATH — scenario_validator

**Objective:** Add PYTHONPATH to `uv run python3 -m scripts.scenario_validator`

**File:** `skills/tide/SKILL.md`

**Change:**
```
Before:
  uv run python3 -m scripts.scenario_validator \

After:
  PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.scenario_validator \
```

## Task 3: Fix SKILL.md PYTHONPATH — format_checker + artifact_manifest

**Objective:** Add PYTHONPATH to `scripts.format_checker` and `scripts.artifact_manifest` invocations

**File:** `skills/tide/SKILL.md`

**Change:**
```
Before:
  uv run python3 -m scripts.format_checker
  uv run python3 - <<'PY'
  from scripts.artifact_manifest import collect_artifact, write_manifest

After:
  PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.format_checker
  PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 - <<'PY'
  from scripts.artifact_manifest import collect_artifact, write_manifest
```

## Task 4: Fix case-writer setup_class style

**Objective:** Change `def setup_class(cls)` → `def setup_class(self)` and `cls.req` → `self.req` in case-writer.md

**File:** `agents/case-writer.md`

**Changes:**
- All `def setup_class(cls):` → `def setup_class(self):`
- All `cls.req =` → `self.req =`
- All references to `cls.req` in examples → `self.req`
