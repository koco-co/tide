# Iteration 11 Score

## Status

Fresh Claude Code + Tide run completed after cleaning old generated Tide artifacts and leaving only the required SparkThrift metadata-sync HAR in `.tide/trash`.

Iter11 fixed the Iter10 input-selection failure: `.tide/parsed.json` selected `/Users/poco/Projects/dtstack-httprunner/.tide/trash/20260509_152002_20260509_150847_172.16.122.52.har`, generated 49 scenarios, and produced tests under `testcases/scenariotest/assets/`.

However, hard gates are still not green. `metadata_direct_test.py` generated 21 `test_*` methods inside classes named `SyncTaskTest`, `DataSourceTest`, `JobQueryTest`, and `TableQueryTest`; pytest does not collect those classes because they do not start with `Test`.

## Six-Dimension Score

| Dimension | Weight | Iter10 | Iter11 | Delta | Evidence |
|---|---:|---:|---:|---:|---|
| 用户体验 | 15% | 55 | 82 | +27 | Natural prompt worked after cleanup; final summary is useful, but still no incremental progress during the Claude run. |
| 自动化流程度 | 25% | 65 | 72 | +7 | Correct HAR and 49 scenarios were generated, but scoped collect silently collected only 28/49 tests unless the metadata file was checked alone. |
| 人工干预度 | 10% | 85 | 88 | +3 | No prompts during generation; required target cleanup and post-run audit remain manual. |
| 代码生成质量 | 25% | 72 | 74 | +2 | Dynamic IDs and project request wrappers improved, but 21 generated tests are uncollectable and format output has 4 FC14 errors plus many FC05 issues. |
| 历史代码契合度 | 15% | 70 | 86 | +16 | Uses `AssetsBaseRequest` / `MetaDataRequest`, `AssetsApi`, `setup_method`, and `allure.step`; class naming violates pytest conventions. |
| 场景理解与编排 | 10% | 35 | 88 | +53 | Correct SparkThrift HAR, 28 endpoints, 49 unique scenarios, 100% confidence >= medium. |

**Weighted total:** 78.9/100

Iter11 is a meaningful recovery from Iter10, but it is not close enough to claim the `>=90` target because a whole generated file is invisible to pytest.

## Ten-Item Deduction Ledger

| # | Item | Iter11 Result | Evidence |
|---:|---|---|---|
| 1 | 硬编码 ID/URL/token | PASS for business IDs | No secret/token matches and no `99999999`; generated IDs are dynamic `dataSourceId`/`tableId`, with one `tableId=0` fallback warning. |
| 2 | Low confidence 过多 | PASS | `high=28`, `medium=21`, `low=0`; 100% medium-or-higher. |
| 3 | `scenario_id` 重复 | PASS | `total=49 unique=49`. |
| 4 | L4/L5 缺失 | PARTIAL | Generated direct/param tests focus on L1-L3; no strong evidence of DB-level L4 or source-evidence L5 checks. |
| 5 | 类粒度不符 | FAIL | `metadata_direct_test.py` classes are `SyncTaskTest`, `DataSourceTest`, `JobQueryTest`, `TableQueryTest`, so pytest collects 0 tests from that file. |
| 6 | 缺 param/boundary/linkage | PARTIAL | Includes 28 direct replay and 21 param-validation scenarios, but no clear boundary/linkage chain. |
| 7 | 敏感信息明文 | PASS | `rg` over generated files found no token/password/webhook/secret values. |
| 8 | 无进度反馈 | FAIL | `session.log` contains only the final summary, not live phase progress. |
| 9 | 无总结报告 | PASS | `session.log` summarizes HAR parse, files, methods, scenario types, and validation claims. |
| 10 | 无增量生成/CI 模板 | FAIL | Iter11 did not improve CI template or incremental generation. |

## Remediation Added In This Iteration

1. Added `FC14` to `scripts.format_checker`: any class containing `test_*` methods must start with `Test`.
2. Added a regression test proving `class SyncTaskTest: def test_*` is flagged as an ERROR.
3. Updated `agents/case-writer.md` to make `Test`-prefixed class names a hard requirement and explicitly forbid `SyncTaskTest`-style names.

## Top 5 Next Optimizations

1. Re-run Claude after installing FC14/prompt changes and require `python -m scripts.format_checker <generated files>` to be zero-error before accepting output.
2. Add an explicit generated-test count gate: compare expected scenario/test counts with `pytest --collect-only` node count per file, not just exit code.
3. Improve FC04 to avoid false positives on Allure titles like `POST /dassets/v1/...` while still flagging literal request URLs.
4. Enforce assert messages or lower FC05 noise so format output stays actionable.
5. Add L4/L5 acceptance criteria for write/linkage scenarios and fail the run when they are missing.
