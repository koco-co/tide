# Iter 22 Score

Score: 91.2/100 conditional, hard gate failed.

## Six-Dimension Score

| Dimension | Weight | Iter 21 | Iter 22 | Delta | Evidence |
|---|---:|---:|---:|---:|---|
| 用户体验 | 15% | 95 | 95 | +0 | CLI exits cleanly: `iter22-exit-status.txt:1-4`. |
| 自动化流程度 | 25% | 93 | 95 | +2 | Final report now marks Assertion Gate failure by default: `final-report.md:5`, `final-report.md:33-38`. |
| 人工干预度 | 10% | 95 | 95 | +0 | No manual termination or prompt supplementation. |
| 代码生成质量 | 25% | 88 | 88 | +0 | `pytest_run.txt:8-9` passes, but `generated_assertion_gate.txt:2-6` fails strict L4/L5 coverage. |
| 历史代码契合度 | 15% | 90 | 90 | +0 | `class_granularity.txt` and `write_scope_verify.txt` pass. |
| 场景理解与编排 | 10% | 84 | 84 | +0 | Scenario count/confidence pass, but no real L4/L5 runtime chain. |

Weighted score: 91.2/100.

## Ten-Item Deduction Ledger

| # | Item | Iter 22 Result | Evidence |
|---:|---|---|---|
| 1 | 硬编码 ID/URL/token | PASS | `format_checker.txt`: all checks passed. |
| 2 | Low confidence 过多 | PASS | `scenario_validator.txt`: ratio `1.0`. |
| 3 | `scenario_id` 重复 | PASS | `scenario_validator.txt`: validator ok. |
| 4 | L4/L5 缺失 | FAIL | `generated_assertion_gate.txt:5-61`: missing L4/L5 across all scenarios. |
| 5 | 类粒度不符 | PASS | `class_granularity.txt`: max one method per class. |
| 6 | 缺 param/boundary/linkage | FAIL | No generated runtime linkage assertion; final report calls out missing L4/L5. |
| 7 | 敏感信息明文 | PASS | `format_checker.txt`: all checks passed. |
| 8 | 无进度反馈 | PARTIAL | CLI exits and final report is honest; session log remains minimal. |
| 9 | 无总结报告 | PASS | `final-report.md:1-38`. |
| 10 | 无增量生成/CI 模板 | PARTIAL | No CI template yet. |

## Top 5 Next Improvements

1. Generate real L4 assertions using target fixtures/services instead of response-literal contract tests.
2. Generate real L5 assertions for the metadata-sync to data-map chain.
3. Convert the final report "partial" status into a nonzero Tide command exit when assertion gate fails.
4. Add progress output that is visible in `session.log`.
5. Add a CI template that runs all strict gates.
