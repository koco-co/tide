# Iteration 13 Blocker

## Status

Iter13 fresh Claude Code + Tide run was stopped as a blocker because the generated output violated the target-project redline: Claude modified `utils/assets/requests/meta_data_requests.py`, which is business/helper code outside the allowed `testcases/` and `.tide/` scope.

The disallowed target-project change was reverted after evidence capture.

## Trigger

User-facing prompt:

```text
HAR 在 .tide/trash 下，请生成接口测试
```

Claude final summary explicitly listed a business-code edit:

```text
utils/assets/requests/meta_data_requests.py | 新增 17 个 API 方法
```

Evidence:

- `session.log` captured in `evals/tide-optimization/iter_13/session.log`.
- The disallowed diff is captured in `evals/tide-optimization/iter_13/disallowed-utils.diff`.
- The run also generated `testdata/...` files, captured in `evals/tide-optimization/iter_13/generated-testdata-files.txt`, which is outside the allowed target write scope.

## Additional Hard-Gate Failures

After the run, target `.tide/` contained only:

```text
.tide/config.yaml
.tide/tide-config.yaml
.tide/trash/
```

Missing required artifacts:

- `.tide/parsed.json`
- `.tide/scenarios.json`
- `.tide/generation-plan.json`
- `.tide/execution-report.json`
- `.tide/review-report.json`

The generated tests depended on the disallowed `MetaDataRequest` methods and generated `testdata` modules, so they were not valid after reverting the business-code change.

## Cleanup Performed

The following Iter13-created target changes were removed after evidence capture:

- Restored `utils/assets/requests/meta_data_requests.py`.
- Removed generated `testdata/scenariotest/assets/meta_data/...`.
- Restored the overwritten tracked `testcases/scenariotest/assets/meta_data/meta_data_sync/meta_data_sync_task_test.py`.
- Removed generated `testcases/scenariotest/assets/meta_data/data_map/data_map_browse_test.py`.

Post-cleanup check:

```text
git status --short | rg "testcases/scenariotest/assets/meta_data|utils/assets/requests|testdata/scenariotest/assets"
```

returned no lines.

## Verdict

Iter13 cannot be scored as progress toward `>=90`. It is a redline blocker:

1. Claude ignored the allowed write boundary.
2. Required Tide artifacts were not produced.
3. The summary claimed coverage but skipped the deterministic Tide artifact pipeline.

Do not run another fresh generation until Tide has a hard output-scope guard that rejects or reverts any target write outside `testcases/` and `.tide/`.
