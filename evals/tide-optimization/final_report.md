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
| Iter 22 | 91.2 | Default final report now marks Assertion Gate failure; strict L4/L5 runtime assertions still missing. |
| Iter 23 | 93.8 | Generated assertion hard gate passes after L4/L5 contract assertions and global scenario dedupe; 28 generated tests pass. |

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
- Iter 22 updates the default Tide command/skill workflow so final reports must include the assertion gate and mark the run failed/partial when L4/L5 are missing.
- Iter 23 updates deterministic fallback generation to emit executable L4/L5 contract assertions and globally dedupe scenario IDs across generation-plan workers.

## Residual Risks

- Iter 23 passes the strict generated assertion gate, but L4/L5 depth is still HAR-backed contract coverage rather than full target-native DB/UI linkage verification.
- Iter 23 required a post-Claude deterministic writer rerun after the dedupe fix; use a fresh full Claude run for final release proof if strict hands-free evidence is required.
- The target repo has pre-existing unrelated dirty/untracked files; Tide write-scope verification covers forbidden-path changes but does not clean the whole target repo.

## Conclusion

The plugin improved materially from the 72/100 baseline and reaches 93.8/100 verified in Iter 23. The strict generated assertion, collect, pytest, format, class granularity, and write-scope gates now pass for the 28-endpoint target run. Remaining work is depth and release hardening: project-native DB/UI L4/L5 checks, a machine-readable final status gate, and a fresh fully hands-free proof run after the latest dedupe patch.
