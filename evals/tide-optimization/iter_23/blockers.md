# Iter 23 Blockers

## Closed

- Missing generated L4/L5 assertions: closed for strict generated assertion gate. `generated_assertion_gate.txt` reports 28 checked scenarios, 28 generated tests, and no violations.
- Duplicate scenario emission across generation-plan workers: closed in `scripts/deterministic_case_writer.py` by global `scenario_id` dedupe. `class_granularity.txt` now reports 28 classes and max one test method.
- Pytest execution confidence: closed for current generated output. `pytest_run.txt` reports 28 passed.

## Remaining Risks

- L4/L5 depth is still deterministic contract coverage over HAR-derived response schema and business envelope values. It is not yet full project-native DB persistence or UI/API linkage verification.
- Iter 23 needed a post-Claude deterministic writer rerun after the duplicate-emission fix. A fresh full Claude run should be used before broad release if end-to-end hands-free proof is required.
- Final status is report-based; there is still no standalone `final_status_gate` that exits nonzero when final reports and hard gates disagree.
