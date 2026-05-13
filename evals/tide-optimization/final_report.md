# Tide Optimization Final Report

PR: https://github.com/koco-co/tide/pull/1

## Trend

| Iteration | Score | Outcome |
|---|---:|---|
| Baseline | 72.0 | Starting point from prior audit. |
| Iter 9 | 83.75 | Added stricter audit around hardcoded IDs; fresh Claude run blocked. |
| Iter 10 | 65.0 | Regression: ambiguous `.tide/trash` selected the wrong HAR. |
| Iter 11 | 78.9 | Correct HAR, but generated classes were not pytest-collectable. |
| Iter 12 | 88.4 | Best project-native run: 27 passed, but missing scenario artifact and noisy reports. |
| Iter 14 | 84.0 | Assisted recovery; write-scope guard verified. |
| Iter 15 | 88.0 | Claude command/hook activation improved. |
| Iter 16 | 82.0 | Autonomous run failed before tests due budget/resume issues. |
| Iter 17 | 86.0 | Deterministic fallback produced passing tests after budget exhaustion. |
| Iter 18 | 90.0 | Guarded fallback produced 28 passing tests with clean format/write-scope gates. |
| Iter 19 | 90.55 | Scoped fallback remediation: one `Test*` class per endpoint, still blocked by L4/L5 and CLI termination. |
| Iter 20 | 86.95 | Fresh natural-language run still did not exit; new assertion hard gate correctly fails all missing L4 checks. |
| Iter 21 | 90.7 | PostToolUse auto-stop fixed CLI termination; strict gate still fails because L4/L5 plans are empty. |

## Improvements Delivered

- Natural-language Claude requests are routed to Tide with `/tide:tide --quick --yes --non-interactive`.
- UserPromptSubmit hook creates the target write-scope snapshot before Claude can write files.
- PreToolUse hook blocks forbidden target business-code writes and direct free-form `tide_generated*.py` writes.
- Scenario normalizer repairs duplicate IDs, missing endpoint IDs, missing confidence, and missing scenario type.
- Scenario validator enforces endpoint coverage, scenario uniqueness, confidence ratio, and generation-plan references.
- Deterministic fallback writer emits sanitized, collectable pytest files with no HAR host/token/business-ID leakage.
- Iter 18 target evidence shows 28 generated tests passing and no forbidden business-code changes.
- Iter 19 deterministic fallback output uses one `Test*` class per endpoint for the current 28-endpoint target run.
- Iter 20 adds FC15 and `generated_assertion_gate` so L4/L5 placeholders or omissions are no longer hidden by green pytest/format checks.
- Iter 21 adds a natural-language auto-stop sentinel and PostToolUse hook; the CLI run exits cleanly after final report generation.

## Residual Risks

- L4/L5 scenario plans are still empty (`db_verify: []`, `ui_verify: []`) in Iter 21; no project-native runtime assertions are implemented.
- The final report currently lists L4/L5 as "待补充" but does not fail the default run status on that basis.
- The target repo has pre-existing unrelated dirty/untracked files; Tide write-scope verification covers forbidden-path changes but does not clean the whole target repo.

## Conclusion

The plugin improved materially from the 72/100 baseline and reaches 90.7/100 conditionally in Iter 21 after fixing hands-free Claude CLI completion. It should not be declared complete against the strict hard-gate objective because real L4/L5 runtime assertions remain unresolved.
