# Iter 18 Quality Gate

Date: 2026-05-13

Target repo: `/Users/poco/Projects/dtstack-httprunner`
HAR input: `.tide/trash/20260509_152002_20260509_150847_172.16.122.52.har`

## Natural-language Claude run

Command:

```bash
claude --plugin-dir /Users/poco/.claude/plugins/cache/tide/tide/1.3.0 --permission-mode bypassPermissions --effort high --max-budget-usd 3.00 -p 'HAR 在 .tide/trash 下，请生成接口测试'
```

Result: the hook created `.tide/write-scope-snapshot.json`, Claude produced parsed/scenario/plan artifacts, and the deterministic fallback wrote two generated pytest files. The Claude process did not exit cleanly and was killed after artifacts were present.

Generated files:

```text
testcases/scenariotest/assets/tide_generated/tide_generated_metadata_test.py
testcases/scenariotest/assets/tide_generated/tide_generated_assets_test.py
```

## Verification

```text
make test
189 passed
```

```text
scenario_validator
ok=true
endpoint_count=28
scenario_count=28
confidence_medium_or_high_ratio=1.0
worker_count=2
```

```text
py_compile
passed
```

```text
pytest --collect-only
28 collected
```

```text
format_checker
All format checks passed!
```

```text
pytest generated files
28 passed, 1 warning in 35.51s
```

```text
write_scope_guard
ok=true
checked_files=1040
added=[]
removed=[]
modified=[]
```

## Notes

Iter 18 hardened the natural-language path by creating the write-scope snapshot in the UserPromptSubmit hook and blocking direct Claude writes to `testcases/**/tide_generated*.py`. This forced generated tests through the deterministic writer and prevented failing free-form generated files from remaining in the target repo.
