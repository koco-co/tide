# Iter16 Score

Overall: **82.0 / 100 — Autonomous Run Failed / Hold**

## Breakdown

| Dimension | Score | Notes |
| --- | ---: | --- |
| Correct HAR and parsing | 95 | Claude run generated `parsed.json` with 28 endpoints from the target HAR. |
| Artifact completeness | 70 | Parse, project assets, scenarios, and generation plan exist; tests, execution report, pytest output, and artifact manifest are missing. |
| Scenario quality | 55 | `scenarios.json` has 65 scenarios but only 64 unique IDs, so validator rejects it. |
| Generated test quality | 0 | No Tide test files were generated in the fresh autonomous run. |
| Write-scope safety | 100 | Snapshot verification passed with no forbidden-path changes. Bash write guard was installed before this run. |
| Automation | 70 | `/tide:tide` now starts and reaches intermediate artifacts, but budget exhaustion and resume hang prevent completion. |

## Conclusion

Iter16 proves the command entrypoint is no longer a pure activation blocker, and hook safety held under a real target run. The quality target is still not met because the autonomous workflow fails before producing valid scenarios and tests.
