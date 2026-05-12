# using-tide

Initialize Tide for a pytest API automation project in Cursor.

## Usage

```text
using-tide [--force]
```

## Instructions

1. Apply the Tide initialization project rule.
2. Resolve `PROJECT_ROOT="$(pwd -P)"`.
3. Resolve `TIDE_PLUGIN_DIR` to the Tide repository root containing `scripts/`, `agents/`, and `prompts/`.
4. Classify the project as existing automation or new automation.
5. For existing automation, run `scripts.convention_scanner` and read `agents/project-scanner.md`.
6. For new automation, collect project context and choose a pytest stack.
7. Configure `repo-profiles.yaml`, `tide-config.yaml`, `.env`, and optional hooks.
8. Run `scripts.scaffold` and validate the initialized project.

## Guardrails

- Preserve existing pytest layout, fixtures, API clients, auth flow, and runner scripts.
- Keep secrets outside generated tests.
- End with a concise summary of captured conventions and the next `tide <har-file>` command.
