# tide

Generate pytest API automation tests from a HAR recording using Tide in Cursor.

## Usage

```text
tide <har-file-path> [--quick] [--yes] [--non-interactive] [--resume] [--wave N]
```

## Instructions

1. Apply the Tide core project rule.
2. Resolve `PROJECT_ROOT="$(pwd -P)"`.
3. Resolve `TIDE_PLUGIN_DIR` to the Tide repository root containing `scripts/`, `agents/`, and `prompts/`.
4. Parse arguments with `scripts.run_context` and write `.tide/run-context.json`.
5. Parse the HAR with `scripts.har_parser`.
6. Analyze scenarios with `agents/scenario-analyzer.md` and validate with `scripts.scenario_validator`.
7. Generate tests with `agents/case-writer.md`.
8. Review with `agents/case-reviewer.md`, run the narrow generated pytest scope, and summarize the results.

## Guardrails

- Keep existing project test configuration intact unless the user approves a specific change.
- Prefer reusable project helpers from `.tide/project-assets.json` and `.tide/convention-fingerprint.yaml`.
- In no-source mode, generate lower-confidence assertions from HAR evidence instead of pretending source tracing was available.
