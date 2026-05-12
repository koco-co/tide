# /tide

Use Codex with the `$tide` skill to generate pytest API tests from a HAR recording.

In Claude Code plugin CLI/non-interactive contexts, use the namespaced command
`/tide:tide <har_file> --yes --non-interactive`. If `/tide` reports
`Unknown command`, retry with `/tide:tide`; do not free-generate tests outside
the Tide workflow.

## Arguments

- `har_file`: path to a `.har` file.
- `--quick`, `--yes`, `--non-interactive`: use conservative defaults for optional confirmations.
- `--resume`: continue from existing `.tide` state.
- `--wave N`: continue from a specific Tide wave.

## Workflow

1. Activate the Codex `$tide` skill.
2. Resolve the installed plugin root as `TIDE_PLUGIN_DIR`.
3. Validate and parse the HAR with Tide's deterministic scripts.
4. Analyze scenarios, generate pytest files, review generated code, and run the narrowest useful validation scope.
5. Summarize generated files, checks run, failures classified, and any manual follow-up.

In non-interactive runs, after `.tide/scenarios.json` and `.tide/generation-plan.json`
exist, run the deterministic fallback before spending more model budget:

```bash
PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.scenario_normalizer \
  --parsed "$PROJECT_ROOT/.tide/parsed.json" \
  --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
  --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json"

PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.deterministic_case_writer \
  --project-root "$PROJECT_ROOT" \
  --parsed "$PROJECT_ROOT/.tide/parsed.json" \
  --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
  --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json"
```

This fallback may be refined by Claude afterwards, but it prevents a run from
ending with valid HAR parsing and no collectable test files.

## Guardrails

- Keep existing project configuration intact unless the user approves a specific change.
- Prefer existing API clients, fixtures, and naming conventions.
- Use `request_user_input` only when Plan Mode exposes it and a material choice needs confirmation.
- Do not assume parallel subagents are available unless the user explicitly asks for them.
