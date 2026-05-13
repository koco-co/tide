# Iter 20 Quality Gate

Status: FAIL. This iteration improved the gate itself, but the generated output still does not satisfy the user's strict hard gates.

## User Simulation

- Command: `claude --plugin-dir /Users/poco/.claude/plugins/cache/tide/tide/1.3.0 --permission-mode bypassPermissions --effort high --max-budget-usd 3.00 -p 'HAR 在 .tide/trash 下，请生成接口测试'`
- Backup before cleanup: target project `.tide.backup.iter_20_20260513_024049`.
- Claude CLI did not exit naturally. Evidence: `iter20-exit-status.txt:1-2` records `exit_code=143` and `duration_seconds=772`, meaning the process was killed after artifacts had already been generated.
- Session log remained empty, so screenshot/session-log evidence is incomplete for UX scoring.

## Gate Results

| Gate | Result | Evidence |
|---|---|---|
| Scenario normalization | PASS | `scenario_normalizer.txt`: `ok=true`, `scenario_count=28`. |
| Scenario validation and confidence | PASS | `scenario_validator.txt:2-7`: 28 endpoints, 28 scenarios, confidence ratio `1.0`, 2 workers. |
| Syntax compile | PASS | `py_compile_after_fc15_regen.txt:1`: `exit_code=0`. |
| Format and sensitive literal checks | PASS after regeneration | `format_checker_after_fc15_regen.txt:1-2`: all checks passed, exit 0. |
| Placeholder L4/L5 blocked | PASS as a gate improvement | `format_checker_fc15_before_regen.txt:1-20` shows FC15 catches skip/assert-true placeholders before regeneration. |
| Pytest collect-only | PASS | `pytest_collect_only_after_fc15_regen.txt` lists 28 collected tests and `exit_code=0`. |
| Pytest execution | PASS | `pytest_run_after_fc15_regen.txt:1-9`: 28 passed, 1 warning, exit 0. |
| Write scope | PASS | `write_scope_verify_after_fc15_regen.txt:1-10`: no added/removed/modified forbidden files. |
| Class granularity | PASS | `class_granularity_after_fc15_regen.txt:1-5`: 28 classes/tests, max one test method per class. |
| Generated assertion hard gate | FAIL | `generated_assertion_gate_after_fc15_regen.txt:1-36`: 28 generated tests checked, all 28 missing L4, exit 1. |

## Hard Gate Decision

Do not treat Iter 20 as complete or promotable.

The practical generated tests are collectable, formatted, and executable, but the strict gate now correctly fails because every scenario's L4 plan is not backed by a real generated L4 assertion. The previous fallback's `assert True` / env-skip L4 placeholders were removed and are now rejected by FC15 rather than counted as quality.
