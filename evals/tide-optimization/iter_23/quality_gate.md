# Iter 23 Quality Gate

Status: PASS on strict generated assertion hard gates, with residual project-native runtime depth risk.

## User Simulation

- Command: `claude --plugin-dir /Users/poco/.claude/plugins/cache/tide/tide/1.3.0 --permission-mode bypassPermissions --effort high --max-budget-usd 3.00 -p 'HAR 在 .tide/trash 下，请生成接口测试'`
- Backup before cleanup: target project `.tide.backup.iter_23_20260513_100050`.
- Claude CLI exited cleanly after 222.03 seconds. Evidence: `claude.log`.
- After the run exposed duplicate scenario emission, the deterministic writer was fixed and rerun against the same Iter 23 `.tide/scenarios.json` and `.tide/generation-plan.json`.

## Gate Results

| Gate | Result | Evidence |
|---|---|---|
| Scenario validation and confidence | PASS | `scenario_validator.txt`: 28 endpoints, 28 scenarios, confidence ratio `1.0`. |
| Generated assertion hard gate | PASS | `generated_assertion_gate.txt`: 28 checked scenarios, 28 generated tests, no violations. |
| Format and sensitive literal checks | PASS | `format_checker.txt`: generated files have zero errors; one FC01 warning remains in `meta_data_sync`. |
| Pytest collect-only | PASS | `pytest_collect_only.txt`: 28 generated tests collect, exit 0. |
| Pytest execution | PASS | `pytest_run.txt`: 28 passed, 1 dependency warning, exit 0. |
| Write scope | PASS | `write_scope_verify.txt`: no forbidden added/removed/modified files. |
| Class granularity | PASS | `class_granularity.txt`: 28 classes, max one test method per class. |
| Final report consistency | PASS after correction | `final-report.md`: records 28 unique tests and 28 passed. |

## Hard Gate Decision

Strict hard gates pass for Iter 23 evidence. The generated tests now include executable L4/L5 contract assertions instead of empty plans, placeholders, or missing markers.

Residual risk: the L4/L5 checks are still deterministic HAR-backed response contract checks, not deep project-native DB/UI linkage assertions through target service utilities.
