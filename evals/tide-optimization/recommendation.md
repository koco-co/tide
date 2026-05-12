# Recommendation

Recommendation: conditional rollout only.

## Can Promote?

Conditional yes for guarded fallback generation in non-production target repos.

No for full autonomous project-native API test generation until the remaining hard-gate gaps are closed.

## Must Do Before Broad Rollout

1. Fix Claude CLI non-termination so a normal user run exits with a final report and nonzero/zero status.
2. Generate real L4 assertions for write operations using existing project DB/query fixtures or explicit `pytest.skip` with actionable wiring instructions.
3. Generate real L5 assertions for SparkThrift metadata-sync to data-map linkage.
4. Add a CI template that runs scenario validation, format checker, collect-only, generated pytest execution, and write-scope verification.

## Use Rules For Current Branch

- Use only with the write-scope hook enabled.
- Treat deterministic fallback output as smoke/contract coverage, not full business-flow validation.
- Run `scripts.format_checker`, `scripts.scenario_validator`, `pytest --collect-only`, generated pytest execution, and `scripts.write_scope_guard verify` before accepting output.
- Do not accept generated tests that modify `api/`, `dao/`, `utils/`, `config/`, `testdata/`, or `resource/`.
- Keep target `.tide` backups before every rerun.
