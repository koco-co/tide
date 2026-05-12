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

## Guardrails

- Keep existing project configuration intact unless the user approves a specific change.
- Prefer existing API clients, fixtures, and naming conventions.
- Use `request_user_input` only when Plan Mode exposes it and a material choice needs confirmation.
- Do not assume parallel subagents are available unless the user explicitly asks for them.
