# Iter 19 Score

Score: 91/100 scoped fallback quality, not complete objective.

## Six-Dimension Score

| Dimension | Weight | Iter 18 | Iter 19 | Delta | Evidence |
|---|---:|---:|---:|---:|---|
| 用户体验 | 15% | 90 | 90 | +0 | No fresh natural-language run; CLI non-termination remains from Iter 18. |
| 自动化流程度 | 25% | 90 | 91 | +1 | Deterministic regeneration preserves manifest, collect, pytest, format, and write-scope gates. |
| 人工干预度 | 10% | 88 | 88 | +0 | Scoped remediation was manual; no new user-flow improvement. |
| 代码生成质量 | 25% | 90 | 93 | +3 | `class_granularity.txt` shows 28 classes for 28 tests, max one method per class; pytest remains 28 passed. |
| 历史代码契合度 | 15% | 84 | 88 | +4 | Class granularity now aligns with the target rule: each endpoint has its own `Test*` class. |
| 场景理解与编排 | 10% | 90 | 90 | +0 | Same Iter 18 scenario artifacts: 28 endpoints, 28 scenarios, 100% high confidence. |

Weighted score: 90.55/100.

## Ten-Item Deduction Ledger

| # | Item | Iter 19 Result | Evidence |
|---:|---|---|---|
| 1 | 硬编码 ID/URL/token | PASS | `format_checker.txt`: all checks passed. |
| 2 | Low confidence 过多 | PASS | Iter 18/19 scenario artifacts remain 28 high confidence scenarios. |
| 3 | `scenario_id` 重复 | PASS | Iter 18 validator remained clean before regeneration. |
| 4 | L4/L5 缺失 | FAIL | Generated fallback still lacks project-native runtime L4/L5 assertions. |
| 5 | 类粒度不符 | PASS | `class_granularity.txt`: 28 generated test classes, one method each. |
| 6 | 缺 param/boundary/linkage | PARTIAL | Scenario artifacts are endpoint-direct; no new param/boundary/linkage generation in this scoped remediation. |
| 7 | 敏感信息明文 | PASS | `format_checker.txt`: all checks passed. |
| 8 | 无进度反馈 | FAIL | No fresh CLI progress run; Iter 18 CLI log remained empty. |
| 9 | 无总结报告 | PASS | `quality_gate.md`, this `score.md`, and blockers are present. |
| 10 | 无增量生成/CI 模板 | PARTIAL | Deterministic regeneration is incremental over existing artifacts, but no CI template was added. |

## Top 5 Next Improvements

1. Generate real L4 checks for write scenarios using target DB/query fixtures.
2. Generate real L5 checks for metadata-sync to data-map linkage.
3. Fix Claude CLI non-termination after artifacts are generated.
4. Add a CI template that runs the full Tide quality gate.
5. Add progress events or `.tide/progress.json` updates during long natural-language runs.
