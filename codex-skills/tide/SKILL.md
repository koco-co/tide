---
name: tide
description: "Use when generating pytest API tests from a HAR file in Codex. Trigger examples: $tide <har-path>, /tide <har-path>, generate API tests from this HAR recording."
---

# Tide for Codex

Generate pytest API tests from a browser HAR recording, reusing Tide's deterministic Python scripts plus the existing `agents/`, `prompts/`, and `references/` assets.

## Runtime Contract

- Work from the user's target automation project as `PROJECT_ROOT="$(pwd -P)"`.
- Set `TIDE_PLUGIN_DIR` to the installed Tide plugin root, the directory containing `.codex-plugin/plugin.json`.
- Prefer deterministic scripts before model-authored artifacts. Run them with `PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH"`.
- Maintain a Codex progress checklist with `update_plan` when available.
- In Plan Mode, use `request_user_input` for material confirmations. In Default mode, ask a concise plain-text question only when a risky decision cannot be inferred.
- Do not default to parallel subagents. For Codex v1, perform the workflow locally and sequentially unless the user explicitly requests subagents or parallel agent work.
- Do not change existing project test configuration unless the user has approved the reason and scope.

## Arguments

Accept a HAR path plus optional flags:

- `<har-file-path>`: required unless resuming.
- `--quick`, `--yes`, or `--non-interactive`: skip optional confirmations and choose conservative defaults.
- `--resume`: continue from `.tide/state.json`.
- `--wave N`: resume from a specific wave.

Use `scripts.run_context` to normalize the arguments and write `.tide/run-context.json`.

```bash
export PROJECT_ROOT="$(pwd -P)"
export TIDE_PLUGIN_DIR="${TIDE_PLUGIN_DIR:-<absolute path to installed Tide plugin root>}"
mkdir -p "$PROJECT_ROOT/.tide"
PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 - <<'PY' > "$PROJECT_ROOT/.tide/run-context.json"
import json
import os
from pathlib import Path
from scripts.run_context import resolve_run_context

ctx = resolve_run_context(
    argument_text=os.environ.get("ARGUMENTS", ""),
    project_root=Path(os.environ["PROJECT_ROOT"]),
    plugin_dir=Path(os.environ["TIDE_PLUGIN_DIR"]),
)
print(json.dumps({
    "project_root": str(ctx.project_root),
    "plugin_dir": str(ctx.plugin_dir),
    "tide_dir": str(ctx.tide_dir),
    "har_path": str(ctx.har_path),
    "requires_confirmation": ctx.args.requires_confirmation,
    "quick": ctx.args.quick,
    "yes": ctx.args.yes,
    "non_interactive": ctx.args.non_interactive,
    "resume": ctx.args.resume,
    "wave": ctx.args.wave,
}, ensure_ascii=False, indent=2))
PY
```

## Workflow

### 0. Preflight

1. Check Python, `uv`, and `git`.
2. Validate `repo-profiles.yaml` and `tide-config.yaml` if present.
3. Detect no-source mode when no backend repositories are configured.
4. Load `.tide/convention-fingerprint.yaml` when present and select prompt modules from `prompts/code-style-python/`.
5. Validate the HAR and scan auth headers:
   ```bash
   PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.har_inputs "$HAR_PATH" --project-root "$PROJECT_ROOT"
   ```
6. Confirm privacy/cost only when confirmation is required. Use `request_user_input` in Plan Mode; otherwise ask plainly.
7. Capture test granularity as `single_api`, `crud`, `e2e_chain`, or `hybrid`; default to `hybrid`.

### 1. Parse and Prepare

1. Initialize Tide state:
   ```bash
   PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.state_manager init --har "$HAR_PATH"
   ```
2. Parse the HAR into `.tide/parsed.json`.
3. Sync configured repositories with `scripts.repo_sync` when repos are configured.
4. Generate `.tide/project-assets.json` deterministically when reusable project utility classes can be discovered.
5. Summarize endpoints, selected granularity, no-source status, and reusable assets before continuing.

### 2. Analyze Scenarios

1. Read `agents/scenario-analyzer.md`, `prompts/scenario-enrich.md`, `prompts/assertion-layers.md`, and `.tide/parsed.json`.
2. Produce `.tide/scenarios.json` and `.tide/generation-plan.json`.
3. Validate both files:
   ```bash
   PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.scenario_validator \
     --parsed "$PROJECT_ROOT/.tide/parsed.json" \
     --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
     --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json"
   ```
4. If validation fails, repair once using the same analyzer prompt. If it still fails, stop and write `.tide/final-report.md`.

### 3. Generate Test Code

1. Read `.tide/generation-plan.json`, `.tide/scenarios.json`, `.tide/project-assets.json`, and selected style prompt modules.
2. Use `agents/case-writer.md` to generate each planned pytest file, preserving the target project's conventions.
3. Run `py_compile` on generated Python files.
4. Run the format checker:
   ```bash
   PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.format_checker <generated-test-dir>
   ```
5. Fix blocking generated-code issues once, then rerun checks.

### 4. Review, Execute, and Deliver

1. Use `agents/case-reviewer.md` and `prompts/review-checklist.md` for static review.
2. Run collection before execution:
   ```bash
   "${PYTHON_BIN:-python3}" -m pytest --collect-only -q
   ```
3. Run the narrow generated test scope first, then broaden only when useful.
4. Classify failures as test defect, environment issue, or suspected business defect.
5. Write `.tide/review-report.json`, `.tide/execution-report.json`, and `.tide/artifact-manifest.json`.
6. Summarize generated files, validation results, commands run, and remaining manual actions.
