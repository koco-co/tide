#!/usr/bin/env bash
# Tide 开发同步脚本：将当前开发目录的改动快速同步到插件安装目录
# 用法: bash scripts/sync-dev.sh [--watch]
set -euo pipefail

PLUGIN_DIR=""

# 从 installed_plugins.json 查找 Tide 插件安装路径
find_plugin_dir() {
    local config="$HOME/.claude/plugins/installed_plugins.json"
    if [ ! -f "$config" ]; then
        echo "错误: 未找到 $config" >&2
        echo "请确认 Tide 插件已安装: /tide" >&2
        return 1
    fi
    PLUGIN_DIR=$(python3 -c "
import json
with open('$config') as f:
    data = json.load(f)
for entries in data.get('plugins', {}).values():
    for e in entries:
        p = e.get('installPath', '')
        if 'tide' in p:
            print(p)
            exit(0)
exit(1)
" 2>/dev/null) || true

    if [ -z "$PLUGIN_DIR" ]; then
        echo "错误: 未找到 Tide 插件安装目录" >&2
        return 1
    fi
    echo "插件目录: $PLUGIN_DIR"
}

sync_files() {
    local src="${1:-.}"
    local dst="${2:-$PLUGIN_DIR}"

    echo "同步中..."
    rsync -av --delete \
        --exclude=".venv" \
        --exclude=".git" \
        --exclude=".worktrees" \
        --exclude=".tide" \
        --exclude="__pycache__" \
        --exclude="*.pyc" \
        --exclude=".pytest_cache" \
        --exclude=".DS_Store" \
        --exclude=".coverage" \
        --exclude="*.egg-info" \
        --exclude="dist" \
        --exclude="htmlcov" \
        "$src/" "$dst/" 2>&1 | tail -10

    # Update git commit SHA in installed_plugins.json
    local sha
    sha=$(git rev-parse HEAD 2>/dev/null || echo "dev")
    python3 -c "
import json, time
config = '$HOME/.claude/plugins/installed_plugins.json'
with open(config) as f:
    data = json.load(f)
for entries in data.get('plugins', {}).values():
    for e in entries:
        if 'tide' in e.get('installPath', ''):
            e['gitCommitSha'] = '$sha'
            e['lastUpdated'] = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
with open(config, 'w') as f:
    json.dump(data, f, indent=2)
print('SHA updated:', '$sha')
" 2>/dev/null || true

    echo "同步完成 ✅"
    echo ""
    echo "变更文件清单:"
    git diff --name-only HEAD 2>/dev/null || echo "(非 git 工作区)"
}

watch_mode() {
    echo "启动文件监听模式 (每 3 秒检查)..."
    echo "按 Ctrl+C 停止"
    local last_sha
    last_sha=$(find . -name "*.py" -o -name "*.md" -o -name "*.sh" | grep -v ".venv" | grep -v ".git" | xargs md5 2>/dev/null | md5)
    while true; do
        sleep 3
        local current_sha
        current_sha=$(find . -name "*.py" -o -name "*.md" -o -name "*.sh" | grep -v ".venv" | grep -v ".git" | xargs md5 2>/dev/null | md5)
        if [ "$current_sha" != "$last_sha" ]; then
            echo "[$(date +%H:%M:%S)] 检测到文件变更..."
            sync_files
            last_sha=$current_sha
        fi
    done
}

# --- 主流程 ---
cd "$(dirname "$0")/.."

find_plugin_dir || exit 1

if [ "${1:-}" = "--watch" ]; then
    sync_files
    watch_mode
else
    sync_files
fi
