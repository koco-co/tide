# Iter14 Score

Overall: **84.0 / 100 — Assisted / Hold**

## Breakdown

| Dimension | Score | Notes |
| --- | ---: | --- |
| Correct HAR and parsing | 95 | Exact SparkThrift HAR parsed to 28 deduped endpoints. |
| Artifact completeness | 90 | `parsed.json`, `scenarios.json`, `generation-plan.json`, `artifact-manifest.json`, and `execution-report.json` present. |
| Scenario quality | 90 | 28/28 endpoints have direct scenarios; confidence medium/high ratio is 100%. |
| Generated test quality | 78 | 10 tests collect; narrow execution is green but 4 tests skip because the current environment lacks the recorded `test_spark_insert` table. |
| Write-scope safety | 100 | Guard verified no denied target writes after snapshot. |
| Automation | 55 | Claude Code did not run `/tide` autonomously; manual Codex repair was required after partial Claude output. |

## Evidence

- `pytest-output.txt`: `6 passed, 4 skipped, 1 warning in 22.50s`
- `execution-report.json`: final pytest report
- `quality_gate.md`: verification summary
- `final-target-status.txt`: target repo status after cleanup

## Conclusion

Iter14 fixes the Iter13 write-scope risk and produces usable tests under supervision, but it does not restore the historical `>=90` claim because the Claude Code plugin entrypoint is still unreliable in the tested non-interactive mode.
