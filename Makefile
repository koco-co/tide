.PHONY: test test-unit test-quick lint typecheck ci release fmt

test:
	uv run pytest tests/ -v --cov=scripts --cov-report=term-missing

test-unit:
	uv run pytest tests/ -v -m unit --cov=scripts --cov-report=term-missing

test-quick:
	uv run pytest tests/ -v --no-cov

lint:
	uv run ruff check scripts/ tests/
	uv run ruff format --check scripts/ tests/

fmt:
	uv run ruff check --fix scripts/ tests/
	uv run ruff format scripts/ tests/

typecheck:
	uv run pyright scripts/

ci: lint typecheck test

dev:
	@bash scripts/sync-dev.sh

dev-watch:
	@bash scripts/sync-dev.sh --watch

PLUGIN_DIR := $(shell python3 -c "import json; d=json.load(open('$(HOME)/.claude/plugins/installed_plugins.json')); [print(e['installPath']) for v in d.get('plugins',{}).values() for e in v if 'tide' in e.get('installPath','')]" 2>/dev/null)

install-plugin:
	@if [ -z "$(PLUGIN_DIR)" ]; then \
		echo "错误: 未找到 Tide 插件安装目录"; exit 1; fi
	@echo "同步到 $(PLUGIN_DIR)..."
	@rsync -av --exclude=".venv" --exclude=".git" --exclude=".worktrees" \
	  --exclude=".tide" --exclude="__pycache__" --exclude="*.pyc" \
	  --exclude=".pytest_cache" --exclude=".ruff_cache" --exclude=".DS_Store" \
	  . "$(PLUGIN_DIR)/" 2>&1 | tail -5
	@python3 -c "import json,subprocess;d=json.load(open('$(HOME)/.claude/plugins/installed_plugins.json'));sha=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip();all(e.update({'lastUpdated':'$(shell date -u +%Y-%m-%dT%H:%M:%S.000Z)','gitCommitSha':sha}) for v in d.get('plugins',{}).values() for e in v if 'tide' in e.get('installPath',''));json.dump(d,open('$(HOME)/.claude/plugins/installed_plugins.json','w'),indent=2)"
	@echo "Tide 插件已更新 ✅"

release:
	@echo "=== 发布流程 ==="
	@echo "1. 确认 pyproject.toml 版本号已更新"
	@python3 -c "import tomllib; v=tomllib.load(open('pyproject.toml','rb'))['project']['version']; print(f'  当前版本: {v}')"
	@echo "2. git tag v$$(python3 -c \"import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])\")"
	@echo "3. git push origin main --tags"
	@echo "4. 在 GitHub 上创建 Release"
