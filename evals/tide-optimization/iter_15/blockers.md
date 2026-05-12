# Iter15 Remaining Blockers

## B1: Full autonomous target generation still pending

The new hooks and `/tide:tide` command were verified in Claude Code CLI mode, but Iter15 did not run a fresh full generation against:

```text
/Users/poco/Projects/dtstack-httprunner/.tide/trash/20260509_152002_20260509_150847_172.16.122.52.har
```

Promotion to `>=90` still requires:

- clean backup/removal of old Tide-generated target artifacts,
- a fresh Claude Code run through `/tide:tide` or hook-routed natural language,
- target write-scope verification after generation,
- pytest collection/execution for the generated tests,
- artifact manifest and score update based on that run.

## B2: Target repo currently has unrelated dirty files

The target repo still contains pre-existing/user modifications outside this iteration, including:

- `api/assets/assets_api.py`
- `resource/common/msg.json`

These must not be reverted by Tide. A fresh target run should snapshot them before execution and verify the plugin does not modify denied paths.
