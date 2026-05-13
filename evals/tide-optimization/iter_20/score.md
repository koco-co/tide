# Iter 20 Score

Score: 87/100 conditional fallback quality, hard gate failed.

## Six-Dimension Score

| Dimension | Weight | Iter 19 | Iter 20 | Delta | Evidence |
|---|---:|---:|---:|---:|---|
| 用户体验 | 15% | 90 | 82 | -8 | Natural-language CLI generated artifacts but required manual kill: `iter20-exit-status.txt:1-2`. |
| 自动化流程度 | 25% | 91 | 90 | -1 | The flow creates artifacts and tests, but completion is not hands-free; assertion gate now catches missing L4. |
| 人工干预度 | 10% | 88 | 80 | -8 | Manual termination was still required after 772 seconds. |
| 代码生成质量 | 25% | 93 | 88 | -5 | `pytest_run_after_fc15_regen.txt:8-9` passes, but `generated_assertion_gate_after_fc15_regen.txt:2-6` fails strict L4 coverage. |
| 历史代码契合度 | 15% | 88 | 89 | +1 | Class granularity matches one class per endpoint: `class_granularity_after_fc15_regen.txt:1-5`. |
| 场景理解与编排 | 10% | 90 | 88 | -2 | 28 scenarios and 100% medium/high confidence pass, but no real L4 implementation: `scenario_validator.txt:2-7`, `generated_assertion_gate_after_fc15_regen.txt:5-33`. |

Weighted score: 86.95/100.

## Ten-Item Deduction Ledger

| # | Item | Iter 20 Result | Evidence |
|---:|---|---|---|
| 1 | 硬编码 ID/URL/token | PASS | `format_checker_after_fc15_regen.txt:1-2`. |
| 2 | Low confidence 过多 | PASS | `scenario_validator.txt:5-7`: ratio `1.0`. |
| 3 | `scenario_id` 重复 | PASS | `scenario_validator.txt:2-9`: validator ok. |
| 4 | L4/L5 缺失 | FAIL | `generated_assertion_gate_after_fc15_regen.txt:5-33`: 28 missing L4 violations. |
| 5 | 类粒度不符 | PASS | `class_granularity_after_fc15_regen.txt:1-5`. |
| 6 | 缺 param/boundary/linkage | PARTIAL | Scenarios exist for 28 endpoints but still do not generate real linkage/L5 runtime checks. |
| 7 | 敏感信息明文 | PASS | `format_checker_after_fc15_regen.txt:1-2`. |
| 8 | 无进度反馈 | FAIL | `iter20-session.log` is empty and CLI had to be killed. |
| 9 | 无总结报告 | PASS | `.tide/final-report.md` copied to `iter_20/final-report.md`; this score and quality gate are present. |
| 10 | 无增量生成/CI 模板 | PARTIAL | Regeneration is deterministic and manifest-backed; no CI template added. |

## Top 5 Next Improvements

1. Generate real project-native L4 assertions from target fixtures or DB query helpers instead of placeholders.
2. Generate real L5 linkage assertions for metadata-sync to data-map flows.
3. Fix Claude CLI non-termination after `.tide/final-report.md` is written.
4. Wire `generated_assertion_gate` into the Tide run/final quality gate so hard failures are visible by default.
5. Add progress logging that survives non-interactive Claude CLI runs.
