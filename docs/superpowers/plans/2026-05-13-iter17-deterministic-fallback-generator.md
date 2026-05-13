# Iter17 Deterministic Fallback Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic fallback that repairs scenario IDs and generates collectable pytest files from Tide artifacts when Claude Code cannot finish the free-form case-writing phase.

**Architecture:** Introduce `scripts/scenario_normalizer.py` for scenario de-duplication and generation-plan repair, and `scripts/deterministic_case_writer.py` for conservative pytest generation from `parsed.json` + normalized `scenarios.json`. Update Tide command/skill docs to run these deterministic steps before or after Claude-assisted writing in non-interactive mode.

**Tech Stack:** Python 3.12+, pytest, JSON artifact processing, existing Tide validators and format checker.

---

## File Structure

- Create `scripts/scenario_normalizer.py`: reads `.tide/parsed.json`, `.tide/scenarios.json`, `.tide/generation-plan.json`; rewrites duplicate scenario IDs with stable suffixes; updates worker `scenario_ids`; fails if required artifacts are missing.
- Create `scripts/deterministic_case_writer.py`: generates conservative pytest files under `testcases/` from normalized scenarios and parsed HAR payloads.
- Add `tests/test_scenario_normalizer.py`: red/green tests for duplicate repair and plan reference repair.
- Add `tests/test_deterministic_case_writer.py`: red/green tests for collectable test output, no hardcoded sensitive host/token, and L1-L5 assertion marker coverage.
- Modify `commands/tide.md` and `skills/tide/SKILL.md`: instruct Claude Code to call the deterministic normalizer and writer in non-interactive mode, before spending more model budget on manual case writing.

## Task 1: Scenario Normalizer

**Files:**
- Create: `scripts/scenario_normalizer.py`
- Create: `tests/test_scenario_normalizer.py`

- [x] **Step 1: Write failing tests**

Create tests that write a parsed artifact with one endpoint, two duplicate scenarios, and a generation plan that references the duplicate ID twice. Assert `normalize_scenario_artifacts(...)` rewrites the second duplicate to `s1_2`, updates plan references, and passes `validate_scenario_outputs`.

- [x] **Step 2: Run red test**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_scenario_normalizer.py -q
```

Expected: import failure for `scripts.scenario_normalizer`.

- [x] **Step 3: Implement normalizer**

Implement:

```python
def normalize_scenario_artifacts(parsed_path: Path, scenarios_path: Path, generation_plan_path: Path) -> dict[str, Any]:
    ...
```

Rules:

- Preserve first occurrence of each `scenario_id`.
- Rename later duplicates by appending `_2`, `_3`, etc.
- Update generation-plan worker `scenario_ids` in encounter order.
- If a scenario lacks `endpoint_id` and has endpoint method/path, attach the matching parsed endpoint ID.
- Write updated JSON files with `ensure_ascii=False`, `indent=2`.

- [x] **Step 4: Run green test**

Run the same targeted test and expect pass.

## Task 2: Deterministic Case Writer

**Files:**
- Create: `scripts/deterministic_case_writer.py`
- Create: `tests/test_deterministic_case_writer.py`

- [x] **Step 1: Write failing tests**

Create a minimal parsed artifact and normalized scenarios containing:

- one `har_direct` scenario with L1/L2/L3 assertions,
- one write scenario with L4 assertion plan,
- one e2e scenario with L5 assertion plan.

Assert `write_deterministic_cases(...)` writes a pytest file under `testcases/scenariotest/assets/meta_data/`, uses `class Test...`, includes L1/L2/L3/L4/L5 markers, contains no `172.16.122.52`, no `webhook`, and compiles with `py_compile`.

- [x] **Step 2: Run red test**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_deterministic_case_writer.py -q
```

Expected: import failure for `scripts.deterministic_case_writer`.

- [x] **Step 3: Implement writer**

Implement:

```python
def write_deterministic_cases(project_root: Path, parsed_path: Path, scenarios_path: Path, generation_plan_path: Path) -> list[Path]:
    ...
```

Rules:

- Default output path: `testcases/scenariotest/assets/meta_data/tide_generated_metadata_test.py`.
- Use environment variables for runtime IDs and table names instead of HAR literals.
- Generate collectable pytest classes with methods named `test_<safe_scenario_id>`.
- Each generated test uses a local `response` dict derived from the HAR response shape and asserts:
  - L1: response status is 200-like via `response["status_code"] == 200`.
  - L2: required response fields exist.
  - L3: business success fields such as `code == 1` and `success is True` when present.
  - L4: write scenarios include DB verification plan metadata, but runtime DB checks are skipped unless `TIDE_ENABLE_DB_ASSERTIONS=1`.
  - L5: e2e/linkage scenarios include linkage metadata, but runtime linkage checks are skipped unless `TIDE_ENABLE_LINKAGE_ASSERTIONS=1`.
- Write `.tide/artifact-manifest.json` entries for generated tests.

- [x] **Step 4: Run green test**

Run the targeted writer test and expect pass.

## Task 3: Command Contract

**Files:**
- Modify: `commands/tide.md`
- Modify: `skills/tide/SKILL.md`
- Modify: `tests/test_skill_contract.py`

- [x] **Step 1: Add contract tests**

Assert both `commands/tide.md` and `skills/tide/SKILL.md` mention:

- `scripts.scenario_normalizer`
- `scripts.deterministic_case_writer`

- [x] **Step 2: Run red contract test**

Run:

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest tests/test_skill_contract.py -q
```

Expected: contract failure until docs are updated.

- [x] **Step 3: Update command and skill docs**

Document exact non-interactive commands:

```bash
PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.scenario_normalizer \
  --parsed "$PROJECT_ROOT/.tide/parsed.json" \
  --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
  --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json"

PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.deterministic_case_writer \
  --project-root "$PROJECT_ROOT" \
  --parsed "$PROJECT_ROOT/.tide/parsed.json" \
  --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
  --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json"
```

- [x] **Step 4: Run contract green**

Run the contract test and expect pass.

## Task 4: Verification and Install

**Files:**
- No additional source files.

- [x] **Step 1: Run targeted tests**

```bash
UV_CACHE_DIR=/private/tmp/tide-uv-cache uv run pytest \
  tests/test_scenario_normalizer.py \
  tests/test_deterministic_case_writer.py \
  tests/test_skill_contract.py -q
```

- [x] **Step 2: Run full suite**

```bash
rm -f .coverage
UV_CACHE_DIR=/private/tmp/tide-uv-cache make test
```

- [x] **Step 3: Install plugin**

```bash
make install-plugin
```

- [x] **Step 4: Smoke-test against Iter16 artifacts**

Copy Iter16 artifacts to a temporary project, run normalizer and deterministic writer, then run:

```bash
python -m py_compile <generated-test-file>
```

Expected: scenario validator passes and generated tests compile.

## Self-Review

- Spec coverage: addresses Iter16 duplicate scenario ID, no generated tests, budget exhaustion, L1-L5 quality markers, and hardcoded secret/host redlines.
- Placeholder scan: no TBD/TODO implementation placeholders.
- Type consistency: function names and CLI module names match tests and documentation.
