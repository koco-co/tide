# Iter15 Claude Hook Validation

## UserPromptSubmit

Command shape:

```bash
claude --plugin-dir /Users/poco/.claude/plugins/cache/tide/tide/1.3.0 \
  --permission-mode bypassPermissions \
  --tools '' \
  --output-format stream-json \
  --include-hook-events \
  --verbose \
  -p 'HAR 在 .tide/trash 下，请生成接口测试。只说明应该调用哪个 Tide 命令，不要调用工具。'
```

Observed:

- `hook_event`: `UserPromptSubmit`
- Hook output contains `/tide:tide <har-file-or-directory> --yes --non-interactive`
- Hook output contains `不要自由生成测试文件`
- Claude response recommended `/tide:tide .tide/trash --yes --non-interactive`

## PreToolUse

Command shape:

```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/.tide" "$tmp/utils"
touch "$tmp/.tide/run-context.json"
cd "$tmp"
claude --plugin-dir /Users/poco/.claude/plugins/cache/tide/tide/1.3.0 \
  --permission-mode bypassPermissions \
  --tools Write,Edit,MultiEdit \
  --disallowedTools Bash \
  --output-format stream-json \
  --include-hook-events \
  --verbose \
  -p 'Use the Write tool to create utils/x.py containing exactly hello. Do not use bash. If the write is blocked, stop.'
```

Observed:

- `hook_event`: `PreToolUse`
- `hook_name`: `PreToolUse:Write`
- Hook output: `{"decision": "block", "reason": "Tide write-scope violation: utils/x.py is outside .tide/ and testcases/"}`
- `file_exists=no`
