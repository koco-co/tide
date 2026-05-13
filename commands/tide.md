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
3. Validate and parse the HAR with Tide's deterministic scripts from the plugin environment, not the target project's `.venv`.
4. Analyze scenarios, generate pytest files, review generated code, and run the narrowest useful validation scope.
5. Summarize generated files, checks run, failures classified, and any manual follow-up.

Tide scripts run as:

```bash
(cd "$PLUGIN_DIR" && PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.har_parser ...)
```

`PYTHON_BIN` from the target project is reserved for generated pytest execution.
The HAR `base_url` is source metadata only; generated tests must use the
project's configured active environment.

In non-interactive runs, after `.tide/scenarios.json` and `.tide/generation-plan.json`
exist, run the deterministic fallback before spending more model budget:

```bash
(cd "$PLUGIN_DIR" && PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.scenario_normalizer \
  --parsed "$PROJECT_ROOT/.tide/parsed.json" \
  --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
  --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json")

(cd "$PLUGIN_DIR" && PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.deterministic_case_writer \
  --project-root "$PROJECT_ROOT" \
  --parsed "$PROJECT_ROOT/.tide/parsed.json" \
  --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
  --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json")
```

This fallback may be refined by Claude afterwards, but it prevents a run from
ending with valid HAR parsing and no collectable test files.

Before writing `.tide/final-report.md`, run the strict generated assertion gate:

```bash
(cd "$PLUGIN_DIR" && PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.generated_assertion_gate \
  --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
  <generated pytest files>)
```

If this reports `empty L4`, `empty L5`, missing L4, or missing L5, the final
report must mark the run as failed. Do not present green pytest/format results
as full L1-L5 success when the assertion gate fails.

Before writing a success report, run the generated tests and save the real final
pytest output:

```bash
"${PYTHON_BIN:-python3}" -m pytest <generated pytest files> -q \
  > "$PROJECT_ROOT/.tide/final-pytest-output.txt" 2>&1
```

没有 final-pytest-output.txt 时，不得输出成功总结；`.tide/final-report.md`
must mark the run as failed instead of successful.

## Guardrails

- Keep existing project configuration intact unless the user approves a specific change.
- Prefer existing API clients, fixtures, and naming conventions.
- Use `request_user_input` only when Plan Mode exposes it and a material choice needs confirmation.
- Do not assume parallel subagents are available unless the user explicitly asks for them.
