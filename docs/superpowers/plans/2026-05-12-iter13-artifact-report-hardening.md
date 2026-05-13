# Iter13 Artifact Report Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Tide fail or repair loudly when scenario artifacts are missing and make execution reports reflect the final pytest run instead of stale intermediate results.

**Architecture:** Add deterministic Python helpers for the two weak points exposed by Iter12, then update the skill and reviewer contracts to call those helpers. Keep the changes surgical: no generation logic rewrite, no target-project code edits.

**Tech Stack:** Python 3.14, pytest, existing Tide `scripts/` modules, Markdown skill/agent contracts.

---

## File Structure

- Modify `scripts/scenario_validator.py`: add stricter checks for required artifact existence, unique `scenario_id`, confidence auditability, and generation-plan coverage.
- Modify `tests/test_scenario_validator.py`: add red tests for missing `scenarios.json`, duplicate `scenario_id`, and low/missing confidence.
- Modify `scripts/test_runner.py`: add a JSON report writer that builds `.tide/execution-report.json` from the final pytest command output.
- Modify `tests/test_runner_wrapper.py`: add red tests proving the report writer overwrites stale pass/fail counts with final pytest output.
- Modify `skills/tide/SKILL.md`, `codex-skills/tide/SKILL.md`, and `agents/case-reviewer.md`: require the deterministic helpers after scenario analysis and after final pytest execution.

### Task 1: Harden Scenario Artifact Validation

**Files:**
- Modify: `scripts/scenario_validator.py`
- Test: `tests/test_scenario_validator.py`

- [ ] **Step 1: Write failing tests**

Add tests that create temp JSON artifacts and assert:

```python
with pytest.raises(FileNotFoundError):
    validate_scenario_outputs(parsed, missing_scenarios, plan)

with pytest.raises(ValueError, match="duplicate scenario_id"):
    validate_scenario_outputs(parsed, duplicate_scenarios, plan)

with pytest.raises(ValueError, match="confidence"):
    validate_scenario_outputs(parsed, low_confidence_scenarios, plan)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_scenario_validator.py -q
```

Expected: at least one new test fails because duplicate IDs and confidence ratio are not yet checked.

- [ ] **Step 3: Implement minimal validation**

In `validate_scenario_outputs`, add:

```python
if len(scenario_ids) != len([s for s in scenarios if s.get("scenario_id")]):
    raise ValueError("duplicate scenario_id found")
medium_or_high = sum(1 for s in scenarios if s.get("confidence") in {"medium", "high"})
if medium_or_high / len(scenarios) < 0.60:
    raise ValueError("confidence>=medium ratio below 60%")
```

Also report `medium_or_high_count` and `medium_or_high_ratio`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_scenario_validator.py -q
```

Expected: all scenario validator tests pass.

### Task 2: Add Final Pytest Execution Report Writer

**Files:**
- Modify: `scripts/test_runner.py`
- Test: `tests/test_runner_wrapper.py`

- [ ] **Step 1: Write failing tests**

Add a test that writes a stale report, calls `write_execution_report`, and asserts final counts overwrite stale data:

```python
report_path.write_text('{"passed": 17, "failed": 10}')
result = TestResult(passed=27, failed=0, skipped=0, errors=0, success=True, output="27 passed")
write_execution_report(report_path, result, total_tests=27, command=["python", "-m", "pytest"])
doc = json.loads(report_path.read_text())
assert doc["passed"] == 27
assert doc["failed"] == 0
assert doc["overall_status"] == "PASS"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_runner_wrapper.py -q
```

Expected: import or attribute failure because `write_execution_report` does not exist.

- [ ] **Step 3: Implement minimal writer**

Add `write_execution_report(report_path, result, total_tests=None, command=None)` to `scripts/test_runner.py`. It writes JSON with `generated_at`, `overall_status`, `collection_success`, `total_tests`, `passed`, `failed`, `errors`, `skipped`, `command`, and `output_tail`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_runner_wrapper.py -q
```

Expected: all test runner wrapper tests pass.

### Task 3: Wire Helpers Into Contracts

**Files:**
- Modify: `skills/tide/SKILL.md`
- Modify: `codex-skills/tide/SKILL.md`
- Modify: `agents/case-reviewer.md`

- [ ] **Step 1: Update scenario contract**

After scenario analysis, require that missing `.tide/scenarios.json`, duplicate `scenario_id`, or confidence ratio below 60% blocks the run.

- [ ] **Step 2: Update execution-report contract**

After the final narrow generated-test pytest execution, require:

```bash
PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.test_runner report \
  --report "$PROJECT_ROOT/.tide/execution-report.json" \
  --total-tests <collected generated test count> \
  --command-file "$PROJECT_ROOT/.tide/final-pytest-command.txt" \
  --output-file "$PROJECT_ROOT/.tide/final-pytest-output.txt"
```

If CLI support is not added in Task 2, document the Python function call instead.

- [ ] **Step 3: Run contract tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_skill_contract.py tests/test_codex_plugin_contract.py -q
```

Expected: contract tests pass.

### Task 4: Full Verification and Commit

**Files:**
- All modified files.

- [ ] **Step 1: Run targeted tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_scenario_validator.py tests/test_runner_wrapper.py -q
```

Expected: all targeted tests pass.

- [ ] **Step 2: Run full suite**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache make test
```

Expected: all Tide tests pass.

- [ ] **Step 3: Commit**

Use explicit staging, not `git add .`:

```bash
git add scripts/scenario_validator.py tests/test_scenario_validator.py scripts/test_runner.py tests/test_runner_wrapper.py skills/tide/SKILL.md codex-skills/tide/SKILL.md agents/case-reviewer.md
git commit -m "fix(tide): iter 13 - harden artifacts and execution reports"
git push
make install-plugin
```

## Self-Review

Spec coverage:
- Missing scenario/confidence artifacts: Task 1 and Task 3.
- Execution-report mismatch: Task 2 and Task 3.
- TDD and verification: Tasks 1, 2, and 4.

Placeholder scan:
- No TBD/TODO placeholders.

Type consistency:
- `TestResult` and `write_execution_report` are defined in Task 2 and referenced consistently.
