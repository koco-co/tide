# Iteration 10 Score

## Status

Fresh Claude Code + Tide run completed, but generated tests for the wrong HAR. The user-approved natural prompt was `HAR 在 .tide/trash 下，请生成接口测试`; `.tide/trash` contained both the required SparkThrift metadata-sync HAR and `batch_orchestration_rules.har`. Tide chose the batch HAR without asking.

## Six-Dimension Score

| Dimension | Weight | Iter9 | Iter10 | Delta | Evidence |
|---|---:|---:|---:|---:|---|
| 用户体验 | 15% | 86 | 55 | -31 | No progress output for most of the 26-minute run; final `session.log:1` shows the wrong HAR was selected. |
| 自动化流程度 | 25% | 80 | 65 | -15 | The run completed and scoped collect passed, but automation chose the wrong input and full collect still fails. |
| 人工干预度 | 10% | 70 | 85 | +15 | 0 manual prompts during run; however non-interactive flow should have stopped on multiple HAR candidates. |
| 代码生成质量 | 25% | 84 | 72 | -12 | Generated suite collected, but L4/L5 missing and hardcoded nonexistent IDs remain (`test_orchestration_rules_part2.py:133,157,168,179,190`). |
| 历史代码契合度 | 15% | 91 | 70 | -21 | Uses batch project anchors (`BatchSQLBase`, `AddTaskParams`, `batch_global_data`) but not the requested assets metadata-sync anchors. |
| 场景理解与编排 | 10% | 90 | 35 | -55 | Scenario is DAGScheduleX orchestration, not SparkThrift `test_spark_insert` metadata sync/data-map validation. |

**Weighted total:** 65.0/100

This is a regression from Iter9 because the fresh run proved the natural user prompt can produce a plausible but irrelevant test suite.

## Ten-Item Deduction Ledger

| # | Item | Iter10 Result | Evidence |
|---:|---|---|---|
| 1 | 硬编码 ID/URL/token | FAIL | Hardcoded `99999999` task/job IDs in generated tests; FC11 does not yet cover `taskId/jobId` false-invalid patterns strongly enough. |
| 2 | Low confidence 过多 | PASS | `high=15`, `medium=10`, `low=4`; 86.2% medium-or-higher. |
| 3 | `scenario_id` 重复 | PASS | `total=29 unique=29`. |
| 4 | L4/L5 缺失 | FAIL | `.tide/review-report.json` records missing L4 and L5 for generated files. |
| 5 | 类粒度不符 | PARTIAL | One class per generated file, but target scenario and assets anchors are wrong. |
| 6 | 缺 param/boundary/linkage | PARTIAL | Generated batch suite includes param/boundary/linkage, but for the wrong HAR. |
| 7 | 敏感信息明文 | PASS for generated tests | Generated files did not contain token/password/webhook values; full target collect printed sensitive live logs, which is an environment/test-runner risk. |
| 8 | 无进度反馈 | FAIL | `session.log` only contains final summary lines after completion; no incremental progress during the long run. |
| 9 | 无总结报告 | PASS | `session.log:5-37` includes a final generated-files and coverage summary. |
| 10 | 无增量生成/CI 模板 | FAIL | Iter10 did not improve CI template or incremental generation. |

## Top 5 Next Optimizations

1. Stop ambiguous HAR selection: fail/list candidates when `.tide/trash` contains multiple `.har` files and the user did not name one exactly.
2. Extend FC11 to cover `taskId`, `jobId`, `projectId`, and negative-test nonexistent ID literals, or require dynamically computed impossible IDs.
3. Add progress streaming or periodic `.tide/progress.json` updates so long Claude runs are observable.
4. Make full collect safer by detecting target-tree known blockers and reporting scoped generated collect separately without leaking sensitive live logs.
5. Enforce L4/L5 as blocking for write/linkage scenarios in `case-reviewer`, not only advisory review findings.
