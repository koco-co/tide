# Iteration 10 Blockers

## Status

Iteration 10 could not start safely. The target repository is dirty and the cleanup step requires deleting prior Tide-generated artifacts outside the writable sandbox.

## Evidence

- Target git status is dirty before cleanup:
  - branch: `test/tide-init`
  - modified business/non-test files include `.gitignore`, `api/assets/assets_api.py`, and `resource/common/msg.json`
  - generated/untracked artifacts include `.tide.backup.iter_*`, `tests/`, `session.log`, and `testcases/scenariotest/batch/batchv2/dagdependency/orchestration_rules_test.py`
- Requested cleanup command was rejected by the escalation reviewer because it included broad destructive actions in the dirty target repo, especially `rm -rf tests` and multiple deletions outside `.tide`, without explicit approval for those specific paths.
- No Claude Code + Tide fresh generation was run in Iter10.

## Required Approval To Continue

Before continuing the loop, the user must explicitly approve all of the following target-repo actions:

1. Back up `/Users/poco/Projects/dtstack-httprunner/.tide` to `.tide.backup.iter_10`.
2. Delete prior generated `.tide` files except `tide-config.yaml`, `config.yaml`, `trash/`, and `inputs/`.
3. Delete the untracked prior Tide output directory `/Users/poco/Projects/dtstack-httprunner/tests/`.
4. Delete prior generated session files `session.log` and `session_interactive.log`.
5. Optionally delete the unrelated generated batch file `testcases/scenariotest/batch/batchv2/dagdependency/orchestration_rules_test.py`.
6. Run Claude Code with the Tide plugin against the target project and HAR, which will send target project/HAR context to the external Claude service and may write generated tests under `testcases/` and `.tide/`.

No business-code files under `api/`, `dao/`, `utils/`, `config/`, or `resource/` should be modified by this loop.
