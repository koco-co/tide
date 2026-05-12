# Iter16 Blockers

## B1: Claude run exceeds budget before test generation

The first full `/tide:tide` run exited with `Error: Exceeded USD budget (3)` after producing intermediate artifacts only.

## B2: Resume run hangs without observable progress

The resume command remained active for several minutes without changing `.tide` artifact timestamps or writing logs/tests. It was terminated to avoid unbounded spend.

## B3: Scenario output is invalid

The generated `scenarios.json` contains duplicate scenario ID:

```text
dt-center-metadata_POST_dmetadata__syncTask_pageTask_boundary
```

`scripts.scenario_validator` rejects the output with `ValueError: duplicate scenario_id found`.

## B4: No generated tests

The fresh run did not create any `testcases/scenariotest/assets/meta_data/tide_*.py` files, so pytest collection/execution cannot be scored for this iteration.

## Required Next Fix

Move scenario generation and test-file generation out of long free-form Claude reasoning and into smaller deterministic or bounded steps:

- run deterministic parse/project-asset steps before invoking Claude,
- require validator repair loops after each scenario batch,
- generate per-domain test files from validated scenarios only,
- preserve hook-level write protection for both file tools and Bash write commands.
