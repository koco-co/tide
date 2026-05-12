# Iter14 Blockers

## B1: Claude Code print mode does not expose Tide slash command

Command:

```bash
claude --plugin-dir /Users/poco/.claude/plugins/cache/tide/tide/1.3.0 \
  --permission-mode bypassPermissions \
  --effort high \
  -p '/tide .tide/trash/20260509_152002_20260509_150847_172.16.122.52.har'
```

Result:

```text
Unknown command: /tide
```

The same behavior occurs for other plugin commands such as `/code-review`, which suggests this is an execution-mode/plugin-command registration issue rather than Tide command content alone.

## B2: Natural-language Tide workflow prompt hangs after partial artifact creation

The explicit natural-language prompt created `.tide/run-context.json`; a shorter generation prompt created `.tide/scenarios.json` and `.tide/generation-plan.json`. Both runs then stopped making progress with zero stdout in `session.log`, and Codex had to terminate the Claude process.

## B3: Assisted output cannot count as autonomous Tide pass

Codex repaired invalid Claude scenario output, wrote the final tests, regenerated artifacts, and ran verification. The resulting tests are useful, but they do not prove the plugin can autonomously satisfy the quality gates.

## Required next fix

Add a reliable non-interactive entrypoint for Claude Code runs, or document/use the correct invocation mechanism if slash commands are intentionally unavailable in `-p` mode. The entrypoint must:

- resolve the installed Tide plugin root,
- run deterministic preflight/parse/scenario/report steps,
- create and verify the write-scope snapshot,
- fail loudly if it cannot activate the Tide workflow,
- avoid falling back to free-form test generation.
