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

## Residual Risks

- Claude CLI still did not terminate cleanly after generating artifacts in Iter 20; it required SIGTERM after 772 seconds.
- Fallback tests are L1-L3 contract tests; the Iter 20 hard gate reports 28 missing L4 runtime assertions.
- L5 cross-endpoint runtime assertions are not implemented or proven in the current generated target output.
- The target repo has pre-existing unrelated dirty/untracked files; Tide write-scope verification covers forbidden-path changes but does not clean the whole target repo.

## Conclusion

The plugin improved materially from the 72/100 baseline and reached a conditional fallback-quality high point in Iter 19, but Iter 20's stricter verification lowers the defensible score to 86.95/100. It should not be declared complete against the strict hard-gate objective because real L4/L5 runtime assertions and hands-free Claude process completion remain unresolved.
