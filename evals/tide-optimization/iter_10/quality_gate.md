# Iteration 10 Quality Gate

## Scope

Fresh Claude Code + Tide run after explicit user approval. User prompt was natural language only: `HAR 在 .tide/trash 下，请生成接口测试`.

## Preparation

| Gate | Result | Evidence |
|---|---:|---|
| Tide branch not `main` | PASS | `git status --short --branch` showed `codex/tide-iter-9-audit-quality-gates...origin/codex/tide-iter-9-audit-quality-gates`. |
| Tide pulled latest | PASS | `git pull --ff-only` returned `Already up to date.` |
| Target `.tide` backup before cleanup | PASS | Created `/Users/poco/Projects/dtstack-httprunner/.tide.backup.iter_10`. |
| `.tide` cleaned to allowed files | PASS | Post-clean listing retained `.tide/config.yaml`, `.tide/tide-config.yaml`, and `.tide/trash/*`. |

## Claude/Tide Run

| Gate | Result | Evidence |
|---|---:|---|
| Session log captured | PASS | `evals/tide-optimization/iter_10/session.log`, 37 lines. |
| Correct HAR selected | FAIL | `session.log:1` says Tide generated from `batch_orchestration_rules.har`; target requirement was SparkThrift metadata sync HAR `20260509_152002_20260509_150847_172.16.122.52.har`. |
| Correct target scenario | FAIL | `.tide/parsed.json:3` has `source_har: ".tide/trash/batch_orchestration_rules.har"`; `.tide/scenarios.json:6` starts with `DAGScheduleX_POST_api_rdos_batch_batchTask_e2e_chain`. |
| Output location | PARTIAL | Tests went under `testcases/...` as required, but generated data went under `testdata/...`; see `session.log:14-16`. |

## Hard Gates

| Gate | Result | Evidence |
|---|---:|---|
| Full target `pytest --collect-only` | FAIL | `.venv/bin/python3 -m pytest --collect-only -q` exited 2 with 75 collection errors, mainly `cx_Oracle` and existing stream/testdata import failures. |
| Scoped generated collect-only | PASS | `.venv/bin/python3 -m pytest testcases/scenariotest/batch/batchv2/tasks/orchestration_rules --collect-only -q` collected 30 generated tests and exited 0. |
| L1/L2/L3 per interface | PARTIAL | Generated files assert status code and response fields, e.g. `test_orchestration_rules.py:91-114`; wrong HAR prevents accepting this for the target scenario. |
| Write-operation L4 | FAIL | `.tide/review-report.json` reports missing L4 database-level assertions for both generated test files. |
| Linkage L5 | FAIL | `.tide/review-report.json` reports missing L5 source evidence annotations. |
| No hardcoded ID/URL/token | FAIL | Generated tests use hardcoded nonexistent IDs: `test_orchestration_rules_part2.py:133`, `:157`, `:168`, `:179`, `:190`; scenarios also include `projectId: 101` and `taskId: 99999999` at `.tide/scenarios.json:32`, `:230`, `:289`. |
| No sensitive plaintext in generated tests | PASS | `rg` over generated `testcases/` and `testdata/` found no token/password/webhook values in generated files. |
| Class/import/fixture fit | PARTIAL | Uses project batch anchors `BatchSQLBase`, `AddTaskParams`, and `batch_global_data` at `test_orchestration_rules.py:9-11,70`; target requested assets metadata-sync anchors, so scenario fit fails. |
| `scenario_id` unique | PASS | `jq` check: `total=29 unique=29`. |
| `>=60% confidence>=medium` | PASS | confidence distribution: high=15, medium=10, low=4; 25/29 = 86.2% medium-or-higher. |

## Verdict

Hard gates are **not green**. Iter10 exposed a product-level UX failure: when `.tide/trash` contained multiple HAR files and the user provided a natural directory prompt, Tide silently chose the wrong HAR. The remediation in this branch adds deterministic ambiguous-HAR detection via `scripts.har_inputs.resolve_har_input` and updates the skill instructions to ask/fail instead of guessing.
