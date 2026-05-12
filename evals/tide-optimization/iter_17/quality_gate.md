# Iter 17 Quality Gate

Date: 2026-05-13

Target repo: `/Users/poco/Projects/dtstack-httprunner`
HAR input: `.tide/trash/20260509_152002_20260509_150847_172.16.122.52.har`

## Natural-language Claude run

Command:

```bash
claude --plugin-dir /Users/poco/.claude/plugins/cache/tide/tide/1.3.0 --permission-mode bypassPermissions --effort high --max-budget-usd 3.00 -p 'HAR 在 .tide/trash 下，请生成接口测试'
```

Result: Claude Code routed the natural-language request through the Tide plugin and produced `.tide/parsed.json`, `.tide/scenarios.json`, and `.tide/generation-plan.json`, then stopped on budget:

```text
Error: Exceeded USD budget (3)
```

## Artifact quality

Scenario validator:

```text
ok=true
endpoint_count=28
scenario_count=28
confidence_medium_or_high_count=28
confidence_medium_or_high_ratio=1.0
worker_count=3
```

Generated output:

```text
testcases/scenariotest/assets/meta_data/tide_generated_metadata_test.py
28 collected tests
2 generated pytest classes
495 lines
```

## Verification

```text
make test
186 passed
```

```text
python3 -m py_compile tide_generated_metadata_test.py
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
pytest generated file
28 passed, 1 warning in 33.70s
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

The generated tests are deterministic fallback contract tests using sanitized response schema metadata. They intentionally do not embed HAR hosts, tokens, full payloads, or hardcoded business IDs.
