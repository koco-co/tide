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
- Do not guess which HAR to use. If the user says the HAR is in `.tide/trash` or provides a directory, run `scripts.har_inputs.resolve_har_input` first. When multiple `.har` files exist, ask for the exact file in interactive mode, or stop in non-interactive mode with the candidate list and an exact command example.

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

Then resolve the HAR path deterministically before validation or parsing:

```bash
export HAR_PATH="$(PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 - <<'PY'
import json
import os
from pathlib import Path
from scripts.har_inputs import resolve_har_input

project_root = Path(os.environ["PROJECT_ROOT"])
ctx = json.loads((project_root / ".tide" / "run-context.json").read_text())
print(resolve_har_input(ctx["har_path"], project_root))
PY
)"
echo "Resolved HAR: $HAR_PATH"
```

If this command reports `Multiple HAR files found; Do not guess`, do not select the newest or most plausible HAR. Ask the user for one exact candidate in interactive mode; in non-interactive mode, stop and print a command such as `$tide .tide/trash/<exact-file>.har --yes --non-interactive`.

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
4. Do not skip this validation. Missing `.tide/scenarios.json`, duplicate `scenario_id`, or a `confidence>=medium` ratio below 60% is a blocking error.
5. If validation fails, repair once using the same analyzer prompt. If it still fails, stop and write `.tide/final-report.md`.

### 3. Generate Test Code

1. Read `.tide/generation-plan.json`, `.tide/scenarios.json`, `.tide/project-assets.json`, and selected style prompt modules.
2. Before any generated file is written, snapshot the target write scope:
   ```bash
   PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.write_scope_guard snapshot \
     --project-root "$PROJECT_ROOT" \
     --snapshot "$PROJECT_ROOT/.tide/write-scope-snapshot.json"
   ```
   Only `.tide/` and `testcases/` are writable. Do not create or edit `api/`, `dao/`, `utils/`, `config/`, `testdata/`, or `resource/`.
3. Use `agents/case-writer.md` to generate each planned pytest file, preserving the target project's conventions.
4. Immediately verify the target write scope:
   ```bash
   PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.write_scope_guard verify \
     --project-root "$PROJECT_ROOT" \
     --snapshot "$PROJECT_ROOT/.tide/write-scope-snapshot.json"
   ```
   If verification fails, stop and report the forbidden paths. Do not continue to pytest or a success summary.
5. Run `py_compile` on generated Python files.
6. Run the format checker:
   ```bash
   PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.format_checker <generated-test-dir>
   ```
7. Fix blocking generated-code issues once, then rerun checks.
8. Re-run write-scope verification after any fix.

### 4. Review, Execute, and Deliver

1. Use `agents/case-reviewer.md` and `prompts/review-checklist.md` for static review.
2. Re-run write-scope verification after case-reviewer changes. If verification fails, stop and report forbidden paths.
3. Run collection before execution:
   ```bash
   "${PYTHON_BIN:-python3}" -m pytest --collect-only -q
   ```
4. Run the narrow generated test scope first, then broaden only when useful.
5. Classify failures as test defect, environment issue, or suspected business defect.
6. Write `.tide/review-report.json`, `.tide/execution-report.json`, and `.tide/artifact-manifest.json`.
7. After the final narrow pytest run, rewrite `.tide/execution-report.json` from the final pytest output so it cannot contain stale intermediate counts:
   ```bash
   set +e
   "${PYTHON_BIN:-python3}" -m pytest <generated-files> -q > "$PROJECT_ROOT/.tide/final-pytest-output.txt" 2>&1
   PYTEST_RC=$?
   set -e
   PYTHONPATH="$TIDE_PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.test_runner report \
     --report "$PROJECT_ROOT/.tide/execution-report.json" \
     --output-file "$PROJECT_ROOT/.tide/final-pytest-output.txt" \
     --return-code "$PYTEST_RC" \
     --total-tests <collect-only generated test count> \
     --command "${PYTHON_BIN:-python3}" -m pytest <generated-files> -q
   ```
8. Summarize generated files, validation results, commands run, and remaining manual actions.
