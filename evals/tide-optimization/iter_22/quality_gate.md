# Iter 22 Quality Gate

Status: FAIL on strict L4/L5 hard gate. PASS on honest final-report status.

## User Simulation

- Command: `claude --plugin-dir /Users/poco/.claude/plugins/cache/tide/tide/1.3.0 --permission-mode bypassPermissions --effort high --max-budget-usd 3.00 -p 'HAR 在 .tide/trash 下，请生成接口测试'`
- Backup before cleanup: target project `.tide.backup.iter_22_20260513_094736`.
- Natural-language CLI exited cleanly. Evidence: `iter22-exit-status.txt:1-4` records `exit_code=0`, `duration_seconds=156`.

## Gate Results

| Gate | Result | Evidence |
|---|---|---|
| Scenario validation and confidence | PASS | `scenario_validator.txt`: 28 endpoints, 28 scenarios, confidence ratio `1.0`. |
| Format and sensitive literal checks | PASS | `format_checker.txt`: all checks passed. |
| Pytest collect-only | PASS | `pytest_collect_only.txt` lists 28 collected tests and exit 0. |
| Pytest execution | PASS | `pytest_run.txt:1-9`: 28 passed, 1 warning, exit 0. |
| Write scope | PASS | `write_scope_verify.txt`: no forbidden added/removed/modified files. |
| Class granularity | PASS | `class_granularity.txt`: 28 classes/tests, max one test method per class. |
| Final report honesty | PASS | `final-report.md:5` marks the run as partial because Assertion Gate failed; `final-report.md:33-38` lists missing L4/L5. |
| Generated assertion hard gate | FAIL | `generated_assertion_gate.txt:1-64`: 28 generated tests checked; L4/L5 missing across all scenarios. |

## Hard Gate Decision

Do not mark complete.

Iter 22 verifies that the default workflow now surfaces the assertion hard-gate failure in `.tide/final-report.md` instead of hiding it behind green pytest/format checks. The remaining product gap is still real L4/L5 runtime assertion generation.
