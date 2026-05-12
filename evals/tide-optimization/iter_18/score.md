# Iter 18 Score

Score: 90/100

## Improvements

- Natural-language prompt flow now creates a write-scope snapshot before target writes.
- Direct Claude writes to `tide_generated*.py` are blocked; generated tests come from the deterministic writer.
- Scenario artifacts validate cleanly: 28 endpoints, 28 scenarios, 100% medium-or-high confidence.
- Generated output is split into two files and 28 collectable pytest tests.
- Format checker passes with zero issues.
- Target generated tests execute successfully: 28 passed.
- Forbidden target business-code scope remained unchanged.

## Remaining Gaps

- Claude CLI still did not exit cleanly after artifacts were generated; it required manual termination.
- Generated tests are deterministic L1-L3 contract tests, not full project-native API-client tests with L4/L5 runtime assertions.
- The session log is empty because Claude produced artifacts without terminal output before termination.

## Assessment

Iter 18 reaches the 90-point bar for guarded natural-language generation and hard quality gates, but the non-terminating Claude process remains a concrete reliability issue for the next iteration.
