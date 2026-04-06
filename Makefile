.PHONY: test lint typecheck ci release fmt

test:
	uv run pytest tests/ -v --cov=scripts --cov-report=term-missing

lint:
	uv run ruff check scripts/ tests/
	uv run ruff format --check scripts/ tests/

fmt:
	uv run ruff check --fix scripts/ tests/
	uv run ruff format scripts/ tests/

typecheck:
	uv run pyright scripts/

ci: lint typecheck test

release:
	@echo "1. Bump version in pyproject.toml + PLUGIN.md"
	@echo "2. git tag v$$(python3 -c 'import tomllib; print(tomllib.load(open(\"pyproject.toml\",\"rb\"))[\"project\"][\"version\"])')"
	@echo "3. git push origin main --tags"
	@echo "4. claude plugins publish (if registry supports)"
