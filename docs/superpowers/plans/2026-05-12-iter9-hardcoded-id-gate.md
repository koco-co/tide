# Iter9 Hardcoded ID Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Iter9 audit gap where generated tests can still pass format checks with string numeric business IDs such as `{"dataSourceId": "43"}` or uncovered keys such as `metaId`.

**Architecture:** Keep enforcement in `scripts/format_checker.py` so the same gate applies to Claude Code, Codex, Cursor, and CI. Update `agents/case-writer.md` so generation guidance matches the validator: invalid-ID cases must use dynamically computed impossible IDs rather than string literals copied from HAR.

**Tech Stack:** Python AST validation, pytest, Tide agent prompt markdown.

---

### Task 1: Add Red Tests for FC11 Coverage

**Files:**
- Modify: `tests/test_format_checker.py`

- [x] **Step 1: Write failing tests**

```python
def test_detects_string_numeric_business_ids(self, tmp_path: Path) -> None:
    bad = tmp_path / "test_hardcoded_string_ids.py"
    bad.write_text(
        "class TestHardcodedIds:\n"
        '    """Hardcoded IDs."""\n\n'
        "    def test_bad(self):\n"
        '        payload = {"dataSourceId": "43", "taskType": 1}\n'
        '        assert payload["dataSourceId"] == "43", "uses hardcoded id"\n'
    )
    violations = check_file(str(bad))
    assert any(v.rule.id == "FC11" for v in violations)
```

- [x] **Step 2: Verify red**

Run: `UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_format_checker.py::TestFormatChecker::test_detects_string_numeric_business_ids tests/test_format_checker.py::TestFormatChecker::test_detects_meta_id_business_ids -v --tb=short`

Observed: both tests failed because FC11 did not report violations.

### Task 2: Tighten FC11 Detection

**Files:**
- Modify: `scripts/format_checker.py`
- Test: `tests/test_format_checker.py`

- [x] **Step 1: Implement minimal AST helper**

Detect hardcoded business IDs when a dict key is a known ID key or ends with `Id`/`Ids`, and the value is a numeric literal, numeric string literal, or a list/tuple containing those literals. Keep `0` allowed for root/fallback semantics.

- [x] **Step 2: Verify green**

Run: `UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_format_checker.py -v --tb=short`

Expected: all format checker tests pass.

### Task 3: Align Generation Prompt

**Files:**
- Modify: `agents/case-writer.md`

- [x] **Step 1: Add prohibited string examples**

Document that `"43"` and `"99999999"` under `*Id` keys are hardcoded IDs, even when intended as invalid examples.

- [x] **Step 2: Add dynamic invalid-ID pattern**

Require invalid-ID negative tests to compute an impossible value from observed IDs, for example `invalid_ds_id = str(max(existing_ids) + 999999)` or use a named helper.

### Task 4: Verify Full Tide Suite

**Files:**
- Test: `tests/`

- [x] **Step 1: Run plugin tests**

Run: `UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/ -v --tb=short`

Expected: 157+ tests pass.

- [x] **Step 2: Re-run checker against Iter7 generated files**

Run: `UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run python3 -m scripts.format_checker /Users/poco/Projects/dtstack-httprunner/tests/interface/test_metadata_sync.py /Users/poco/Projects/dtstack-httprunner/tests/interface/test_assets_datamap.py`

Observed: FC11 flags four hardcoded generated IDs in `test_metadata_sync.py`, proving the new gate catches the audit finding.
