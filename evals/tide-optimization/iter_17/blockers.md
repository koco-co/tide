# Iter 17 Blockers

- Budget exhaustion remains the primary blocker for autonomous Claude-authored tests: `Error: Exceeded USD budget (3)`.
- The deterministic fallback intentionally avoids unsafe business-code edits and dynamic ID lookup wiring, so it cannot yet generate high-value L4/L5 assertions for `dtstack-httprunner`.
- Target repo has pre-existing dirty/untracked files unrelated to this iteration; they were preserved and not reverted.
