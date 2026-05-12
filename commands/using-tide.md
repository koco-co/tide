# /using-tide

Use Codex with the `$using-tide` skill to initialize Tide for an API automation project.

## Arguments

- `--force`: refresh Tide configuration after confirming the intended overwrite or update scope.

## Workflow

1. Activate the Codex `$using-tide` skill.
2. Resolve the installed plugin root as `TIDE_PLUGIN_DIR`.
3. Classify the target as an existing automation project or a new automation project.
4. Scan conventions or collect a compact project profile.
5. Configure backend repositories, base URL, auth, environments, optional database access, and output directories.
6. Scaffold Tide files and run the smallest validation check.

## Guardrails

- Preserve existing pytest layout, fixtures, clients, and runner scripts.
- Keep secrets out of generated tests and committed config.
- Use `request_user_input` only when Plan Mode exposes it and a material choice needs confirmation.
- Leave `$tide <har-file>` ready to run after initialization.
