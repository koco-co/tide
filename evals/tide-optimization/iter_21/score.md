# Iter 21 Score

Score: 90.7/100 conditional, hard gate failed.

## Six-Dimension Score

| Dimension | Weight | Iter 20 | Iter 21 | Delta | Evidence |
|---|---:|---:|---:|---:|---|
| 用户体验 | 15% | 82 | 95 | +13 | Natural-language CLI exits cleanly: `iter21-exit-status.txt:1-4`. |
| 自动化流程度 | 25% | 90 | 93 | +3 | Full run creates artifacts, final report, collectable tests, and exits without manual kill. |
| 人工干预度 | 10% | 80 | 95 | +15 | No manual termination or prompt supplementation in Iter 21. |
| 代码生成质量 | 25% | 88 | 88 | +0 | `pytest_run.txt:8-9` passes, but `generated_assertion_gate_refined.txt:2-6` fails strict L4/L5 coverage. |
| 历史代码契合度 | 15% | 89 | 90 | +1 | `class_granularity.txt:1-5` shows one `Test*` class per endpoint and write scope is clean. |
| 场景理解与编排 | 10% | 88 | 84 | -4 | Scenario confidence is 100%, but L4/L5 plans are empty for all scenarios. |

Weighted score: 90.7/100.

## Ten-Item Deduction Ledger

| # | Item | Iter 21 Result | Evidence |
|---:|---|---|---|
| 1 | 硬编码 ID/URL/token | PASS | `format_checker.txt:1-2`. |
| 2 | Low confidence 过多 | PASS | `scenario_validator.txt:5-7`: ratio `1.0`. |
| 3 | `scenario_id` 重复 | PASS | `scenario_validator.txt:2-9`: validator ok after normalization. |
| 4 | L4/L5 缺失 | FAIL | `generated_assertion_gate_refined.txt:5-61`: empty L4/L5 plans for all scenarios. |
| 5 | 类粒度不符 | PASS | `class_granularity.txt:1-5`. |
| 6 | 缺 param/boundary/linkage | FAIL | L4/L5 plans are empty; no real boundary/linkage runtime assertions. |
| 7 | 敏感信息明文 | PASS | `format_checker.txt:1-2`. |
| 8 | 无进度反馈 | PARTIAL | Final report exists and CLI exits; `iter21-session.log` remains nearly empty. |
| 9 | 无总结报告 | PASS | `final-report.md:1-25`. |
| 10 | 无增量生成/CI 模板 | PARTIAL | Deterministic generation is manifest-backed; no CI template added. |

## Top 5 Next Improvements

1. Generate actionable L4 plans from target DB/query fixtures instead of `db_verify: []`.
2. Generate actionable L5 chain plans only for real cross-endpoint flows; do not emit empty `ui_verify: []`.
3. Wire `generated_assertion_gate` into the default Tide final report so the report cannot claim L1-L5 coverage while L4/L5 are empty.
4. Add progress logging to `.tide/progress.json` or session output during non-interactive runs.
5. Add CI template for scenario, format, assertion, collect, pytest, and write-scope gates.
