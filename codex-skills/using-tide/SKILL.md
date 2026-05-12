---
name: using-tide
description: "Use when initializing Tide in a Codex workspace before generating HAR-driven API tests. Trigger examples: $using-tide, /using-tide, initialize Tide for this API automation project."
---

# Using Tide for Codex

Initialize a project so `$tide` can generate pytest API tests from HAR recordings while preserving existing automation conventions.

## Runtime Contract

- Work from the user's automation project as `PROJECT_ROOT="$(pwd -P)"`.
- Set `TIDE_PLUGIN_DIR` to the installed Tide plugin root, the directory containing `.codex-plugin/plugin.json`.
- Prefer deterministic scripts from `$TIDE_PLUGIN_DIR/scripts/` for scanning, scaffolding, and validation.
- Maintain a Codex progress checklist with `update_plan` when available.
- In Plan Mode, use `request_user_input` for material choices. In Default mode, ask a concise plain-text question only when the choice cannot be safely inferred.
- Do not default to parallel subagents. Codex v1 initialization is a local sequential workflow.
- Do not overwrite existing test configuration without explicit user approval.

## Workflow

### 1. Environment and Project Classification

1. Check Python 3.12+, `uv`, and `git`.
2. Detect the target project's Python version from `.python-version`, `pyproject.toml`, or setup metadata.
3. Detect existing automation signals: pytest config, `conftest.py`, test file count, HTTP client helpers, Allure use, CI config.
4. Classify as:
   - `existing_auto` when there are at least three test files and either `conftest.py` or pytest config exists.
   - `new_project` otherwise.

### 2. Existing Automation Project

1. Read `agents/project-scanner.md`.
2. Run the convention scanner:
   ```bash
   export PROJECT_ROOT="$(pwd -P)"
   export TIDE_PLUGIN_DIR="${TIDE_PLUGIN_DIR:-<absolute path to installed Tide plugin root>}"
   PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 "$TIDE_PLUGIN_DIR/scripts/convention_scanner.py" --project-root "$PROJECT_ROOT"
   ```
3. Produce `.tide/project-profile.json` and `.tide/convention-fingerprint.yaml`.
4. Confirm the detected architecture, code style, auth flow, environment config, assertion style, data strategy, and runner strategy. Use `request_user_input` in Plan Mode when a user decision is required.
5. Preserve detected conventions in `tide-config.yaml`.

### 3. New Automation Project

1. Collect a compact industry profile: domain, system type, team size, special compliance needs, and auth complexity.
2. Use `agents/industry-researcher.md` only when current web research is needed; otherwise state that the recommendation is based on local context and model knowledge.
3. Recommend two or three pytest stack options.
4. After selection, write a minimal Tide config and scaffold.

### 4. Repository and Connection Config

1. Configure additional backend source repositories under `.tide/repos/` only when source-aware analysis is desired.
2. Write or update `repo-profiles.yaml`.
3. Capture base URL, auth mode, environment variables, optional database config, and optional notifier config.
4. Keep secrets in `.env` or user-provided secret storage; do not hardcode them into generated tests.

### 5. Scaffold and Validate

1. Render `tide-config.yaml`.
2. Run the scaffold script in the selected mode:
   ```bash
   PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 "$TIDE_PLUGIN_DIR/scripts/scaffold.py" --project-root "$PROJECT_ROOT"
   ```
3. Validate generated config files and run the smallest available smoke test.
4. Summarize how to run `$tide <har-file>`, where Tide state will be written, and which conventions were captured.
