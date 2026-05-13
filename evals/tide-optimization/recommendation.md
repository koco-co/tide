# Recommendation

Recommendation: limited guarded rollout.

## Can Promote?

Yes for guarded fallback generation in non-production target repos when the full Iter 23 gate set is run.

No for claiming full autonomous project-native API test generation until L4/L5 checks use target-native DB/service/linkage verification.

## Must Do Before Broad Rollout

1. Upgrade Iter 23 L4 assertions from HAR-backed response schema contracts to target-native DB/query fixture verification where stable helpers exist.
2. Upgrade Iter 23 L5 assertions from response envelope consistency to cross-endpoint metadata-sync/data-map linkage checks.
3. Convert Assertion Gate failure into a nonzero Tide command exit, not just a partial final-report status.
4. Add a CI template that runs scenario validation, format checker, generated assertion gate, collect-only, generated pytest execution, and write-scope verification.

## Use Rules For Current Branch

- Use only with the write-scope hook enabled.
- Treat deterministic fallback output as smoke/contract coverage, not full business-flow validation.
- Run `scripts.format_checker`, `scripts.scenario_validator`, `scripts.generated_assertion_gate`, `pytest --collect-only`, generated pytest execution, and `scripts.write_scope_guard verify` before accepting output.
- Require `generated_assertion_gate` to show equal scenario and generated-test counts.
- Do not accept generated tests that modify `api/`, `dao/`, `utils/`, `config/`, `testdata/`, or `resource/`.
- Keep target `.tide` backups before every rerun.
