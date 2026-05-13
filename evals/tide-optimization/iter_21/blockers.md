# Iter 21 Blockers

## Resolved: Natural-language CLI non-termination

The PostToolUse auto-stop hook made the normal-user flow exit without manual kill.

Evidence: `iter21-exit-status.txt:1-2` shows `exit_code=0` and `duration_seconds=131`.

## Remaining Blocker 1: Empty L4/L5 plans

The generated scenario artifacts include L4/L5 objects, but the plans are empty (`db_verify: []`, `ui_verify: []`). This is not an actionable runtime assertion plan.

Evidence: `generated_assertion_gate_refined.txt:1-64` reports empty L4 and empty L5 plans for all 28 scenarios.

## Remaining Blocker 2: Final report overstates L1-L5 coverage

The final report lists L4 and L5 as "待补充", which is honest, but it still appears under an "L1-L5 断言覆盖" section. The default flow should run the assertion hard gate and make the final status fail when L4/L5 are empty.

Evidence: `final-report.md:27-33`.

## Decision

The active goal remains incomplete. Iter 21 removes the CLI completion blocker but fails the strict L4/L5 quality gate.
