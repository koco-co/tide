# Iter 20 Blockers

## Blocker 1: Natural-language Claude CLI still does not exit

The Iter 20 user-simulation run produced parsed/scenario/manifest/final-report artifacts and generated tests, but the Claude process did not return by itself. It was terminated after 772 seconds.

Evidence: `iter20-exit-status.txt:1-2`.

## Blocker 2: Strict L4 hard gate fails

The previous fallback generated L4 placeholder code using env-gated skip plus `assert True`. Iter 20 added FC15 so those placeholders are now rejected. After regeneration, placeholders are gone, but the generated tests still lack real L4 assertions for all 28 scenarios.

Evidence:
- Placeholder detection before regeneration: `format_checker_fc15_before_regen.txt:1-20`.
- Missing real L4 after regeneration: `generated_assertion_gate_after_fc15_regen.txt:1-36`.

## Blocker 3: L5 remains unproven

The current scenario artifacts do not produce a real chain assertion path. No generated L5 runtime assertion is present in the current target tests.

## Decision

Stop treating green pytest/format checks as sufficient. They are necessary but not sufficient. The active goal remains incomplete until real L4/L5 assertions and natural CLI completion are verified.
