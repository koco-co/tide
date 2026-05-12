# Iteration 11 Quality Gate

## Scope

Fresh Claude Code + Tide run after explicit user approval to clean old generated Tide artifacts and run Claude Code generation. User prompt was natural language only: `HAR 在 .tide/trash 下，请生成接口测试`.

## Preparation

| Gate | Result | Evidence |
|---|---:|---|
| Tide branch not `main` | PASS | Branch is `codex/tide-iter-9-audit-quality-gates`. |
| Tide latest before run | PASS | Branch was already up to date before Iter11 run. |
| Target `.tide` backup before cleanup | PASS | Created `/Users/poco/Projects/dtstack-httprunner/.tide.backup.iter_11`. |
| Old generated Tide artifacts cleaned | PASS | Removed Iter10 batch generated outputs and left only the required SparkThrift HAR in active `.tide/trash`. |

## Claude/Tide Run

| Gate | Result | Evidence |
|---|---:|---|
| Session log captured | PASS | `evals/tide-optimization/iter_11/session.log`, 32 lines. |
| Correct HAR selected | PASS | `.tide/parsed.json` selected `/Users/poco/Projects/dtstack-httprunner/.tide/trash/20260509_152002_20260509_150847_172.16.122.52.har`. |
| Correct target scenario | PASS | Parsed HAR includes SparkThrift metadata-sync entries including `test_spark_insert`. |
| Output location | PASS | Generated `testcases/scenariotest/assets/assets_datamap_v2_test.py` and `testcases/scenariotest/assets/meta_data_sync/metadata_direct_test.py`. |
| Summary report | PASS | `session.log` reports 28 endpoints, 49 scenarios, 2 generated files, 49 methods. |

## Hard Gates

| Gate | Result | Evidence |
|---|---:|---|
| Scoped generated collect-only | FAIL | Combined collect exited 0 but listed only 28 tests from `assets_datamap_v2_test.py`; metadata file contributed 0 tests. |
| Metadata file collect-only | FAIL | `.venv/bin/python3 -m pytest testcases/scenariotest/assets/meta_data_sync/metadata_direct_test.py --collect-only -q` exited 5 with `no tests ran`. |
| Format checker on metadata file | FAIL | New FC14 reports 4 ERRORs for `SyncTaskTest`, `DataSourceTest`, `JobQueryTest`, and `TableQueryTest`. |
| Format checker on datamap file | PARTIAL | 0 errors, but 29 warnings and 77 issues, mostly FC04 title false positives and FC05 missing assert messages. |
| L1/L2/L3 per interface | PARTIAL | Generated tests assert status code and business response fields, but 21 metadata tests are not collected. |
| Write-operation L4 | PARTIAL | No strong DB-level assertion evidence in generated direct replay/param-validation suite. |
| Linkage L5 | PARTIAL | No clear source-evidence annotations for linkage acceptance. |
| No hardcoded ID/URL/token | PASS | No token/password/webhook/secret/`99999999`; business IDs are dynamic `dataSourceId`/`tableId`, with one `tableId=0` fallback warning. |
| Class/import/fixture fit | FAIL | Request wrappers and imports fit, but four metadata classes violate pytest `Test*` collection naming. |
| `scenario_id` unique | PASS | `total=49 unique=49`. |
| `>=60% confidence>=medium` | PASS | `high=28`, `medium=21`, `low=0`; 49/49 = 100%. |

## New Product Bug

The previous format gate did not model pytest class collection rules. A generated file can contain valid Python and many `test_*` methods while still contributing zero tests if the containing classes do not start with `Test`.

Iter11 adds FC14 and a case-writer hard requirement so future generations should fail fast instead of accepting this invisible-test pattern.

## Verdict

Hard gates are **not green**. Iter11 recovered correct HAR selection and scenario understanding, but generated 21 uncollectable metadata tests. The run scores **78.9/100** and remains below the `>=90` target.
