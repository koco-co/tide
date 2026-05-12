# Iteration 9 Score

## Status

Iter9 is a remediation/audit iteration, not a complete Claude generation iteration. The Claude run was blocked by external data-transfer approval, so this score is based on fresh local verification plus the existing Iter7 generated artifacts.

## Six-Dimension Score

| Dimension | Weight | Iter7 Claim | Iter9 Audited | Delta | Evidence |
|---|---:|---:|---:|---:|---|
| 用户体验 | 15% | 92 | 86 | -6 | Previous final report exists, but fresh audit found hard gate overclaim and full collect failure. |
| 自动化流程度 | 25% | 94 | 80 | -14 | Claude non-interactive run blocked pending explicit external-service approval. |
| 人工干预度 | 10% | 95 | 70 | -25 | Approval is required before rerunning Claude against target data. |
| 代码生成质量 | 25% | 92 | 84 | -8 | Existing generated `test_metadata_sync.py` has four FC11 hardcoded-ID errors under the stricter checker. |
| 历史代码契合度 | 15% | 93 | 91 | -2 | Scoped generated tests still collect 36/36 and use project imports/fixtures, but output path remains `tests/interface/` rather than requested `testcases/`. |
| 场景理解与编排 | 10% | 92 | 90 | -2 | Existing artifacts still include E2E + param/boundary cases, but confidence gate remains weak without a fresh run. |

**Weighted total:** 83.75/100

This does not meet the overall goal because code generation quality is below 85 after the stricter hardcoded-ID audit and hard gates are not all passing.

## Ten-Item Deduction Ledger

| # | Item | Iter9 Result | Evidence |
|---:|---|---|---|
| 1 | 硬编码 ID/URL/token | FAIL on existing generated code; validator fixed | `format_checker` now reports FC11 at `test_metadata_sync.py:180,189,233,378`; fix in `scripts/format_checker.py:276-317`. |
| 2 | Low confidence 过多 | WEAK | Existing Iter7 score says `scenarios.json` lacked confidence; no fresh Claude run possible. |
| 3 | `scenario_id` 重复 | NOT RECHECKED WITH FRESH RUN | No new generation artifacts. Existing Iter7 claimed uniqueness. |
| 4 | L4/L5 缺失 | PARTIAL PASS | Existing generated file contains `_poll_sync_complete()` and E2E lifecycle; no new run. |
| 5 | 类粒度不符 | PARTIAL PASS | Existing generated files collect 36 tests and use project classes; format warnings remain for missing class docstrings. |
| 6 | 缺 param/boundary/linkage | PARTIAL PASS | Existing tests include `param_null`, boundary, and lifecycle tests. |
| 7 | 敏感信息明文 | WEAK | Generated files do not embed tokens in inspected matches, but full target logs/configs contain credentials and live API output. |
| 8 | 无进度反馈 | BLOCKED | No fresh session log because Claude run was rejected. |
| 9 | 无总结报告 | PASS | This `score.md` and `quality_gate.md` record Iter9. |
| 10 | 无增量生成/CI 模板 | NOT IMPROVED | Iter9 focused on FC11 hard gate. |

## Top 5 Next Optimizations

1. Get explicit approval to run Claude Code with the Tide plugin against target-project data, then regenerate and rescore.
2. Make generated negative-ID tests compute missing IDs dynamically via the new case-writer pattern.
3. Add a CI/quality gate that runs `scripts.format_checker` on generated files and fails on FC11.
4. Scope target `pytest --collect-only` to generated Tide files, or fix the target project’s unrelated collect blockers before using full-project collect as a gate.
5. Persist scenario `confidence` in every generated `scenarios.json` and enforce `>=60% medium` in a validator.
