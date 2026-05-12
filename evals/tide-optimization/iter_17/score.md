# Iter 17 Score

Score: 86/100

## Improvements

- Natural-language Claude entrypoint works and routes the prompt to Tide without explicit slash-command input.
- Scenario artifacts are normalized into a validator-clean set: 28 endpoints, 28 scenarios, 100% medium-or-high confidence.
- Deterministic fallback now produces collectable pytest tests after Claude budget exhaustion.
- Generated tests pass local execution in the target repo: 28 passed.
- Format gates are clean: no unused imports, no long-line violations, no hardcoded host/URL/business-ID violations, no overlarge test class warning.
- Write-scope guard remained clean; no forbidden target business-code edits were detected.

## Remaining Gaps

- Claude Code still exhausted the USD 3 budget before writing tests itself.
- The fallback output is conservative L1-L3 schema/status/business-success coverage, not full project-native API-client tests.
- No executable L4 DB or L5 cross-endpoint assertions are produced for this target run.

## Assessment

Iter 17 is a major recovery from Iter 16 because the natural-language flow leaves a usable, validated, passing generated test artifact even when Claude stops on budget. It is not yet a 90+ result because the generated tests are still fallback contract tests rather than project-native end-to-end API tests with L4/L5 assertions.
