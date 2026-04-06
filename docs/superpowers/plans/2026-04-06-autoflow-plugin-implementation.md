# AutoFlow Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `sisyphus-autoflow` Claude Code Plugin — a HAR-driven, source-aware API test automation system with 2 skills, 5 agents, 6 Python scripts, and dual GitHub + Plugin publishing.

**Architecture:** Four-wave orchestration pipeline with 5 specialized AI agents. Python scripts handle deterministic operations (HAR parsing, git sync, state management, scaffolding, notifications, test execution). Markdown files define agent behaviors, prompt templates, and skill entry points. All wired together via a PLUGIN.md manifest.

**Tech Stack:** Python 3.12+ / uv / pydantic / httpx / jinja2 / pyyaml / pytest / ruff / pyright

**Spec:** `docs/superpowers/specs/2026-04-06-autoflow-plugin-design.md`

---

## File Map

### Root Files (create)
- `pyproject.toml` — Plugin dev dependencies, pytest/ruff/pyright config
- `Makefile` — Dev shortcuts: test, lint, typecheck, ci, release
- `LICENSE` — MIT license
- `.gitignore` — Python + plugin-specific ignores
- `PLUGIN.md` — Claude Code Plugin metadata with frontmatter
- `README.md` — GitHub README with Mermaid diagrams
- `.github/workflows/ci.yml` — GitHub Actions CI pipeline

### scripts/ (create, TDD)
- `scripts/__init__.py`
- `scripts/har_parser.py` — HAR JSON parsing, filtering, deduplication, Pydantic models
- `scripts/state_manager.py` — Wave checkpoint CRUD (init/advance/resume/archive)
- `scripts/repo_sync.py` — Git clone/pull/checkout from repo-profiles.yaml
- `scripts/scaffold.py` — Jinja2 template rendering, project structure generation
- `scripts/notifier.py` — Webhook notifications (DingTalk/Feishu/Slack/Custom)
- `scripts/test_runner.py` — pytest invocation wrapper, result collection

### tests/ (create, part of TDD)
- `tests/conftest.py` — Shared fixtures (tmp_path wrappers, sample data loaders)
- `tests/test_har_parser.py`
- `tests/test_state_manager.py`
- `tests/test_repo_sync.py`
- `tests/test_scaffold.py`
- `tests/test_notifier.py`
- `tests/test_runner_wrapper.py`
- `tests/fixtures/sample.har`
- `tests/fixtures/sample_dirty.har`
- `tests/fixtures/sample_repo_profiles.yaml`
- `tests/fixtures/sample_response.json`

### templates/ (create)
- `templates/pyproject.toml.j2`
- `templates/conftest.py.j2`
- `templates/.env.example`

### prompts/ (create)
- `prompts/har-parse-rules.md`
- `prompts/scenario-enrich.md`
- `prompts/assertion-layers.md`
- `prompts/code-style-python.md`
- `prompts/review-checklist.md`

### agents/ (create)
- `agents/har-parser.md`
- `agents/repo-syncer.md`
- `agents/scenario-analyzer.md`
- `agents/case-writer.md`
- `agents/case-reviewer.md`

### skills/ (create)
- `skills/using-autoflow/SKILL.md`
- `skills/autoflow/SKILL.md`

### references/ (create)
- `references/assertion-examples.md`
- `references/tech-stack-options.md`

---

## Task 1: Project Foundation

**Files:**
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `LICENSE`
- Create: `.gitignore`
- Create: `PLUGIN.md`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "sisyphus-autoflow"
version = "0.1.0"
description = "HAR-driven, source-aware API test automation plugin for Claude Code"
requires-python = ">=3.12"
license = "MIT"
dependencies = [
    "pydantic>=2.10",
    "jinja2>=3.1",
    "pyyaml>=6.0",
    "httpx>=0.28",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "ruff>=0.8",
    "pyright>=1.1",
    "pre-commit>=4.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=scripts --cov-report=term-missing --strict-markers"

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TCH"]

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "basic"
```

- [ ] **Step 2: Create Makefile**

```makefile
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
```

- [ ] **Step 3: Create LICENSE (MIT)**

Standard MIT license text with current year and author.

- [ ] **Step 4: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
.venv/

# Plugin working directories (in user projects, not plugin itself)
.autoflow/
.repos/
.trash/

# Environment
.env

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Coverage
htmlcov/
.coverage
coverage.xml
```

- [ ] **Step 5: Create PLUGIN.md**

```markdown
---
name: sisyphus-autoflow
description: "HAR-driven, source-aware API test automation. Generate pytest suites with L1-L5 layered assertions from HAR files + backend source code."
version: "0.1.0"
author: "koco-co"
license: MIT
repository: "https://github.com/koco-co/sisyphus-autoflow"
keywords: ["api-testing", "har", "pytest", "automation", "ai"]
requires:
  bins: ["python3", "uv", "git"]
---

# sisyphus-autoflow

HAR-driven, source-aware API test automation plugin for Claude Code.

## Skills

- `/using-autoflow` — Initialize project environment, configure repos, tech stack, and connections
- `/autoflow <har-file>` — Generate pytest test suites from HAR files with AI-powered source analysis
```

- [ ] **Step 6: Create scripts/__init__.py and tests/__init__.py**

Both empty files to make Python packages.

- [ ] **Step 7: Install dependencies and verify**

Run: `uv sync --dev`
Expected: All dependencies installed successfully.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml Makefile LICENSE .gitignore PLUGIN.md scripts/__init__.py tests/__init__.py
git commit -m "feat: initialize plugin project foundation"
```

---

## Task 2: Test Fixtures

**Files:**
- Create: `tests/fixtures/sample.har`
- Create: `tests/fixtures/sample_dirty.har`
- Create: `tests/fixtures/sample_repo_profiles.yaml`
- Create: `tests/fixtures/sample_response.json`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create sample.har (minimal valid HAR)**

```json
{
  "log": {
    "version": "1.2",
    "creator": {"name": "test", "version": "1.0"},
    "entries": [
      {
        "request": {
          "method": "POST",
          "url": "http://172.16.115.247/dassets/v1/datamap/recentQuery",
          "headers": [
            {"name": "Content-Type", "value": "application/json"},
            {"name": "Cookie", "value": "SESSION=abc123"}
          ],
          "postData": {"mimeType": "application/json", "text": "{}"}
        },
        "response": {
          "status": 200,
          "headers": [{"name": "Content-Type", "value": "application/json;charset=utf-8"}],
          "content": {
            "mimeType": "application/json",
            "text": "{\"code\":1,\"message\":null,\"data\":[],\"success\":true}"
          }
        },
        "time": 45
      },
      {
        "request": {
          "method": "POST",
          "url": "http://172.16.115.247/dassets/v1/datamap/assetStatistics",
          "headers": [{"name": "Content-Type", "value": "application/json"}],
          "postData": {"mimeType": "application/json", "text": "{}"}
        },
        "response": {
          "status": 200,
          "headers": [{"name": "Content-Type", "value": "application/json;charset=utf-8"}],
          "content": {
            "mimeType": "application/json",
            "text": "{\"code\":1,\"message\":null,\"data\":[{\"type\":1,\"count\":100}],\"success\":true}"
          }
        },
        "time": 120
      },
      {
        "request": {
          "method": "POST",
          "url": "http://172.16.115.247/dmetadata/v1/syncTask/pageTask",
          "headers": [{"name": "Content-Type", "value": "application/json"}],
          "postData": {"mimeType": "application/json", "text": "{\"currentPage\":1,\"pageSize\":10}"}
        },
        "response": {
          "status": 200,
          "headers": [{"name": "Content-Type", "value": "application/json;charset=utf-8"}],
          "content": {
            "mimeType": "application/json",
            "text": "{\"code\":1,\"message\":null,\"data\":{\"data\":[],\"totalCount\":0},\"success\":true}"
          }
        },
        "time": 200
      }
    ]
  }
}
```

- [ ] **Step 2: Create sample_dirty.har (with noise)**

Same structure but with additional entries that should be filtered:
- 2 entries for `.js` static resources (GET, 200, text/javascript)
- 1 entry for `.css` (GET, 200, text/css)
- 1 entry for WebSocket upgrade (GET, 101)
- 1 entry for `hot-update.json` (GET, 200)
- 1 duplicate of `recentQuery` (same method+path, different timestamp)
- 1 entry for `recentQuery` with different params (should keep as parameterized data)
- 1 entry for `recentQuery` returning 500 (different status code, keep separately)
- Plus the 3 valid entries from sample.har
Total: 11 entries, 5 should survive filtering+dedup (3 unique endpoints + 1 parameterized + 1 error variant).

- [ ] **Step 3: Create sample_repo_profiles.yaml**

```yaml
profiles:
  - name: dt-center-assets
    path: .repos/CustomItem/dt-center-assets
    branch: release_6.2.x
    url_prefixes:
      - /dassets/v1/
    modules:
      - pattern: "com.dtstack.assets.controller"
        description: "Controller layer"
      - pattern: "com.dtstack.assets.service"
        description: "Service layer"

  - name: dt-center-metadata
    path: .repos/CustomItem/dt-center-metadata
    branch: release_6.2.x
    url_prefixes:
      - /dmetadata/v1/
    modules:
      - pattern: "com.dtstack.metadata.controller"
        description: "Controller layer"

db:
  host: 172.16.115.247
  port: 3306
  user: root
  password: "${DB_PASSWORD}"
  database: dtinsight

notifications:
  - type: dingtalk
    webhook: "${DINGTALK_WEBHOOK}"
```

- [ ] **Step 4: Create sample_response.json**

```json
{
  "code": 1,
  "message": null,
  "data": [
    {"type": 1, "count": 16140},
    {"type": 4, "count": 1323},
    {"type": 5, "count": 116}
  ],
  "space": 0,
  "version": "release_6.2.x",
  "success": true
}
```

- [ ] **Step 5: Create tests/conftest.py**

```python
"""Shared test fixtures for plugin unit tests."""
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_har_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample.har"


@pytest.fixture
def sample_dirty_har_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_dirty.har"


@pytest.fixture
def sample_repo_profiles_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_repo_profiles.yaml"


@pytest.fixture
def sample_response_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_response.json"
```

- [ ] **Step 6: Verify fixtures load**

Run: `uv run pytest tests/ --collect-only`
Expected: Collects 0 tests (no test files yet), but no import errors.

- [ ] **Step 7: Commit**

```bash
git add tests/
git commit -m "feat: add test fixtures and conftest for plugin unit tests"
```

---

## Task 3: HAR Parser (TDD)

**Files:**
- Create: `scripts/har_parser.py`
- Create: `tests/test_har_parser.py`

This is the most critical script — it transforms raw HAR JSON into the structured `parsed.json` format that all downstream agents consume.

- [ ] **Step 1: Write failing tests for Pydantic models**

```python
"""Tests for scripts/har_parser.py"""
import json
from pathlib import Path

import pytest

from scripts.har_parser import (
    HarEntry,
    HarRequest,
    HarResponse,
    ParsedEndpoint,
    ParsedResult,
    parse_har,
    filter_entries,
    dedup_entries,
    match_repo,
)


class TestHarModels:
    def test_har_request_from_entry(self):
        raw = {
            "method": "POST",
            "url": "http://example.com/api/v1/users",
            "headers": [{"name": "Content-Type", "value": "application/json"}],
            "postData": {"mimeType": "application/json", "text": '{"name":"test"}'},
        }
        req = HarRequest.model_validate(raw)
        assert req.method == "POST"
        assert req.url == "http://example.com/api/v1/users"
        assert req.body == {"name": "test"}

    def test_har_response_from_entry(self):
        raw = {
            "status": 200,
            "headers": [{"name": "Content-Type", "value": "application/json;charset=utf-8"}],
            "content": {
                "mimeType": "application/json",
                "text": '{"code":1,"data":[],"success":true}',
            },
        }
        resp = HarResponse.model_validate(raw)
        assert resp.status == 200
        assert resp.body == {"code": 1, "data": [], "success": True}

    def test_har_response_base64_encoded(self):
        import base64
        text = base64.b64encode(b'{"code":1}').decode()
        raw = {
            "status": 200,
            "headers": [],
            "content": {"mimeType": "application/json", "text": text, "encoding": "base64"},
        }
        resp = HarResponse.model_validate(raw)
        assert resp.body == {"code": 1}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_har_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.har_parser'`

- [ ] **Step 3: Implement Pydantic models**

```python
"""HAR file parser — deterministic JSON parsing, filtering, deduplication.

Transforms raw HAR files into structured parsed.json for downstream agents.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, field_validator, model_validator


class HarHeader(BaseModel):
    name: str
    value: str


class HarRequest(BaseModel):
    method: str
    url: str
    headers: list[HarHeader] = []
    postData: dict[str, Any] | None = None

    @property
    def body(self) -> dict[str, Any] | None:
        if not self.postData:
            return None
        text = self.postData.get("text", "")
        if not text:
            return None
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None

    @property
    def path(self) -> str:
        return urlparse(self.url).path

    @property
    def content_type(self) -> str:
        for h in self.headers:
            if h.name.lower() == "content-type":
                return h.value.split(";")[0].strip()
        return ""


class HarContent(BaseModel):
    mimeType: str = ""
    text: str = ""
    encoding: str = ""


class HarResponse(BaseModel):
    status: int
    headers: list[HarHeader] = []
    content: HarContent = HarContent()

    @property
    def body(self) -> dict[str, Any] | None:
        text = self.content.text
        if not text:
            return None
        if self.content.encoding == "base64":
            try:
                text = base64.b64decode(text).decode("utf-8")
            except Exception:
                return None
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None

    @property
    def content_type(self) -> str:
        ct = self.content.mimeType.split(";")[0].strip()
        if ct:
            return ct
        for h in self.headers:
            if h.name.lower() == "content-type":
                return h.value.split(";")[0].strip()
        return ""


class HarEntry(BaseModel):
    request: HarRequest
    response: HarResponse
    time: float = 0


class ParsedEndpoint(BaseModel):
    id: str
    method: str
    path: str
    service: str
    module: str
    request: dict[str, Any]
    response: dict[str, Any]
    matched_repo: str | None = None
    matched_branch: str | None = None


class ParsedSummary(BaseModel):
    total_raw: int
    after_filter: int
    after_dedup: int
    services: list[str]
    modules: list[str]


class ParsedResult(BaseModel):
    source_har: str
    parsed_at: str
    base_url: str
    endpoints: list[ParsedEndpoint]
    summary: ParsedSummary
```

- [ ] **Step 4: Run model tests to verify they pass**

Run: `uv run pytest tests/test_har_parser.py::TestHarModels -v`
Expected: 3 PASSED

- [ ] **Step 5: Write failing tests for filter_entries**

Add to `tests/test_har_parser.py`:

```python
class TestFilterEntries:
    def test_keeps_json_api_requests(self, sample_har_path: Path):
        with open(sample_har_path) as f:
            har = json.load(f)
        entries = [HarEntry.model_validate(e) for e in har["log"]["entries"]]
        filtered = filter_entries(entries)
        assert len(filtered) == 3
        assert all(e.response.content_type == "application/json" for e in filtered)

    def test_drops_static_resources(self, sample_dirty_har_path: Path):
        with open(sample_dirty_har_path) as f:
            har = json.load(f)
        entries = [HarEntry.model_validate(e) for e in har["log"]["entries"]]
        filtered = filter_entries(entries)
        paths = [e.request.path for e in filtered]
        assert not any(p.endswith((".js", ".css", ".png")) for p in paths)

    def test_drops_websocket(self, sample_dirty_har_path: Path):
        with open(sample_dirty_har_path) as f:
            har = json.load(f)
        entries = [HarEntry.model_validate(e) for e in har["log"]["entries"]]
        filtered = filter_entries(entries)
        assert not any(e.response.status == 101 for e in filtered)

    def test_drops_hot_update(self, sample_dirty_har_path: Path):
        with open(sample_dirty_har_path) as f:
            har = json.load(f)
        entries = [HarEntry.model_validate(e) for e in har["log"]["entries"]]
        filtered = filter_entries(entries)
        paths = [e.request.path for e in filtered]
        assert not any("hot-update" in p for p in paths)
```

- [ ] **Step 6: Run filter tests to verify they fail**

Run: `uv run pytest tests/test_har_parser.py::TestFilterEntries -v`
Expected: FAIL — `cannot import name 'filter_entries'`

- [ ] **Step 7: Implement filter_entries**

Add to `scripts/har_parser.py`:

```python
STATIC_EXTENSIONS = {".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".map"}
DROP_PATH_PATTERNS = {"hot-update", "sockjs", "__webpack", "source-map"}


def filter_entries(entries: list[HarEntry]) -> list[HarEntry]:
    """Filter HAR entries: keep only JSON API requests, drop static/WS/noise."""
    result = []
    for entry in entries:
        path = entry.request.path.lower()

        # Drop static resources
        if any(path.endswith(ext) for ext in STATIC_EXTENSIONS):
            continue

        # Drop WebSocket upgrades
        if entry.response.status == 101:
            continue

        # Drop noise patterns
        if any(pattern in path for pattern in DROP_PATH_PATTERNS):
            continue

        # Keep only JSON responses
        if "json" not in entry.response.content_type.lower():
            continue

        result.append(entry)

    return result
```

- [ ] **Step 8: Run filter tests to verify they pass**

Run: `uv run pytest tests/test_har_parser.py::TestFilterEntries -v`
Expected: ALL PASSED

- [ ] **Step 9: Write failing tests for dedup_entries**

Add to `tests/test_har_parser.py`:

```python
class TestDedupEntries:
    def test_merges_same_method_path(self, sample_dirty_har_path: Path):
        with open(sample_dirty_har_path) as f:
            har = json.load(f)
        entries = [HarEntry.model_validate(e) for e in har["log"]["entries"]]
        filtered = filter_entries(entries)
        deduped = dedup_entries(filtered)
        # recentQuery appears multiple times with same params — should merge
        recent_query = [e for e in deduped if "recentQuery" in e.request.path]
        # Should keep: 1 normal + 1 different params + 1 error (500)
        assert len(recent_query) <= 3

    def test_keeps_different_status_codes(self, sample_dirty_har_path: Path):
        with open(sample_dirty_har_path) as f:
            har = json.load(f)
        entries = [HarEntry.model_validate(e) for e in har["log"]["entries"]]
        filtered = filter_entries(entries)
        deduped = dedup_entries(filtered)
        statuses = {e.response.status for e in deduped if "recentQuery" in e.request.path}
        assert 200 in statuses
        assert 500 in statuses
```

- [ ] **Step 10: Implement dedup_entries**

Add to `scripts/har_parser.py`:

```python
def dedup_entries(entries: list[HarEntry]) -> list[HarEntry]:
    """Deduplicate entries: merge same method+path+status, keep different params/statuses."""
    seen: dict[str, HarEntry] = {}
    result = []

    for entry in entries:
        key = f"{entry.request.method}:{entry.request.path}:{entry.response.status}"
        body_str = json.dumps(entry.request.body, sort_keys=True) if entry.request.body else ""
        full_key = f"{key}:{body_str}"

        if full_key not in seen:
            seen[full_key] = entry
            result.append(entry)

    return result
```

- [ ] **Step 11: Run dedup tests**

Run: `uv run pytest tests/test_har_parser.py::TestDedupEntries -v`
Expected: ALL PASSED

- [ ] **Step 12: Write failing tests for match_repo and parse_har**

Add to `tests/test_har_parser.py`:

```python
class TestMatchRepo:
    def test_matches_dassets_prefix(self, sample_repo_profiles_path: Path):
        with open(sample_repo_profiles_path) as f:
            profiles = yaml.safe_load(f)
        repo, branch = match_repo("/dassets/v1/datamap/recentQuery", profiles["profiles"])
        assert repo == "dt-center-assets"
        assert branch == "release_6.2.x"

    def test_matches_dmetadata_prefix(self, sample_repo_profiles_path: Path):
        with open(sample_repo_profiles_path) as f:
            profiles = yaml.safe_load(f)
        repo, branch = match_repo("/dmetadata/v1/syncTask/add", profiles["profiles"])
        assert repo == "dt-center-metadata"
        assert branch == "release_6.2.x"

    def test_returns_none_for_unknown_prefix(self, sample_repo_profiles_path: Path):
        with open(sample_repo_profiles_path) as f:
            profiles = yaml.safe_load(f)
        repo, branch = match_repo("/unknown/v1/something", profiles["profiles"])
        assert repo is None
        assert branch is None


class TestParseHar:
    def test_full_parse(self, sample_har_path: Path, tmp_path: Path):
        profiles_path = Path(__file__).parent / "fixtures" / "sample_repo_profiles.yaml"
        result = parse_har(sample_har_path, profiles_path)
        assert result.source_har == "sample.har"
        assert result.base_url == "http://172.16.115.247"
        assert len(result.endpoints) == 3
        assert result.summary.total_raw == 3
        assert result.summary.after_filter == 3
        assert "dassets" in result.summary.services
        assert "dmetadata" in result.summary.services

    def test_endpoint_has_matched_repo(self, sample_har_path: Path):
        profiles_path = Path(__file__).parent / "fixtures" / "sample_repo_profiles.yaml"
        result = parse_har(sample_har_path, profiles_path)
        dassets_ep = next(e for e in result.endpoints if e.service == "dassets")
        assert dassets_ep.matched_repo == "dt-center-assets"

    def test_raises_on_invalid_har(self, tmp_path: Path):
        bad_har = tmp_path / "bad.har"
        bad_har.write_text("not json")
        with pytest.raises(ValueError, match="Invalid HAR"):
            parse_har(bad_har, None)

    def test_raises_on_empty_entries(self, tmp_path: Path):
        empty_har = tmp_path / "empty.har"
        empty_har.write_text('{"log":{"entries":[]}}')
        with pytest.raises(ValueError, match="No entries"):
            parse_har(empty_har, None)
```

- [ ] **Step 13: Implement match_repo and parse_har**

Add to `scripts/har_parser.py`:

```python
def match_repo(path: str, profiles: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    """Match a URL path to a repo using url_prefixes from profiles."""
    for profile in profiles:
        for prefix in profile.get("url_prefixes", []):
            if path.startswith(prefix):
                return profile["name"], profile.get("branch")
    return None, None


def _extract_service_module(path: str) -> tuple[str, str]:
    """Extract service and module from URL path like /dassets/v1/datamap/recentQuery."""
    parts = [p for p in path.split("/") if p]
    service = parts[0] if parts else "unknown"
    module = parts[2] if len(parts) > 2 else "unknown"
    return service, module


def parse_har(
    har_path: Path,
    profiles_path: Path | None = None,
) -> ParsedResult:
    """Parse a HAR file into structured endpoint data."""
    try:
        with open(har_path) as f:
            har_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"Invalid HAR file: {e}") from e

    raw_entries_data = har_data.get("log", {}).get("entries", [])
    if not raw_entries_data:
        raise ValueError("No entries found in HAR file")

    raw_entries = [HarEntry.model_validate(e) for e in raw_entries_data]
    total_raw = len(raw_entries)

    filtered = filter_entries(raw_entries)
    after_filter = len(filtered)

    deduped = dedup_entries(filtered)
    after_dedup = len(deduped)

    # Load profiles if provided
    profiles: list[dict[str, Any]] = []
    if profiles_path and profiles_path.exists():
        with open(profiles_path) as f:
            config = yaml.safe_load(f)
        profiles = config.get("profiles", [])

    # Extract base URL from first entry
    first_url = deduped[0].request.url if deduped else ""
    parsed_url = urlparse(first_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url.scheme else ""

    # Build endpoints
    endpoints: list[ParsedEndpoint] = []
    services: set[str] = set()
    modules: set[str] = set()

    for i, entry in enumerate(deduped):
        path = entry.request.path
        service, module = _extract_service_module(path)
        services.add(service)
        modules.add(module)

        matched_repo, matched_branch = match_repo(path, profiles) if profiles else (None, None)

        # Strip sensitive headers
        safe_headers = {
            h.name: h.value
            for h in entry.request.headers
            if h.name.lower() not in ("cookie", "authorization", "x-auth-token")
        }

        endpoints.append(
            ParsedEndpoint(
                id=f"ep_{i + 1:03d}",
                method=entry.request.method,
                path=path,
                service=service,
                module=module,
                request={
                    "headers": safe_headers,
                    "body": entry.request.body,
                },
                response={
                    "status": entry.response.status,
                    "body": entry.response.body,
                    "time_ms": int(entry.time),
                },
                matched_repo=matched_repo,
                matched_branch=matched_branch,
            )
        )

    return ParsedResult(
        source_har=har_path.name,
        parsed_at=datetime.now(timezone.utc).isoformat(),
        base_url=base_url,
        endpoints=endpoints,
        summary=ParsedSummary(
            total_raw=total_raw,
            after_filter=after_filter,
            after_dedup=after_dedup,
            services=sorted(services),
            modules=sorted(modules),
        ),
    )
```

- [ ] **Step 14: Run all har_parser tests**

Run: `uv run pytest tests/test_har_parser.py -v`
Expected: ALL PASSED (9+ tests)

- [ ] **Step 15: Lint and typecheck**

Run: `make lint && make typecheck`
Expected: No errors

- [ ] **Step 16: Commit**

```bash
git add scripts/har_parser.py tests/test_har_parser.py
git commit -m "feat: implement HAR parser with filtering, dedup, and repo matching"
```

---

## Task 4: State Manager (TDD)

**Files:**
- Create: `scripts/state_manager.py`
- Create: `tests/test_state_manager.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for scripts/state_manager.py"""
import json
from pathlib import Path

import pytest

from scripts.state_manager import (
    SessionState,
    WaveStatus,
    init_session,
    advance_wave,
    resume_session,
    archive_session,
)


class TestInitSession:
    def test_creates_state_file(self, tmp_path: Path):
        state = init_session(tmp_path, "test.har")
        state_file = tmp_path / ".autoflow" / "state.json"
        assert state_file.exists()

    def test_state_has_session_id(self, tmp_path: Path):
        state = init_session(tmp_path, "test.har")
        assert state.session_id.startswith("af_")

    def test_initial_wave_is_one(self, tmp_path: Path):
        state = init_session(tmp_path, "test.har")
        assert state.current_wave == 0
        assert state.waves["1"].status == WaveStatus.PENDING

    def test_raises_on_existing_session(self, tmp_path: Path):
        init_session(tmp_path, "test.har")
        with pytest.raises(ValueError, match="existing session"):
            init_session(tmp_path, "test2.har")


class TestAdvanceWave:
    def test_advances_to_next_wave(self, tmp_path: Path):
        state = init_session(tmp_path, "test.har")
        updated = advance_wave(tmp_path, 1, {"endpoints_count": 29})
        assert updated.current_wave == 1
        assert updated.waves["1"].status == WaveStatus.COMPLETED
        assert updated.waves["1"].data == {"endpoints_count": 29}

    def test_raises_on_out_of_order(self, tmp_path: Path):
        init_session(tmp_path, "test.har")
        with pytest.raises(ValueError, match="out of order"):
            advance_wave(tmp_path, 3)


class TestResumeSession:
    def test_returns_state(self, tmp_path: Path):
        init_session(tmp_path, "test.har")
        advance_wave(tmp_path, 1)
        state = resume_session(tmp_path)
        assert state.current_wave == 1
        assert state.source_har == "test.har"

    def test_returns_none_when_no_session(self, tmp_path: Path):
        state = resume_session(tmp_path)
        assert state is None


class TestArchiveSession:
    def test_moves_to_history(self, tmp_path: Path):
        state = init_session(tmp_path, "test.har")
        advance_wave(tmp_path, 1)
        advance_wave(tmp_path, 2)
        advance_wave(tmp_path, 3)
        advance_wave(tmp_path, 4)
        archive_session(tmp_path)
        autoflow = tmp_path / ".autoflow"
        assert not (autoflow / "state.json").exists()
        history = autoflow / "history"
        assert history.exists()
        archived = list(history.iterdir())
        assert len(archived) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_state_manager.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement state_manager.py**

```python
"""Wave checkpoint state management — init, advance, resume, archive."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class WaveStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class WaveState(BaseModel):
    status: WaveStatus = WaveStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    agents: list[str] = []
    data: dict[str, Any] = {}


class UserConfirmation(BaseModel):
    confirmed: bool = False
    modifications: list[str] = []
    confirmed_at: str | None = None


class SessionState(BaseModel):
    session_id: str
    source_har: str
    current_wave: int = 0
    waves: dict[str, WaveState] = {}
    user_confirmations: dict[str, UserConfirmation] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_dir(project_root: Path) -> Path:
    return project_root / ".autoflow"


def _state_file(project_root: Path) -> Path:
    return _state_dir(project_root) / "state.json"


def _read_state(project_root: Path) -> SessionState | None:
    sf = _state_file(project_root)
    if not sf.exists():
        return None
    return SessionState.model_validate_json(sf.read_text())


def _write_state(project_root: Path, state: SessionState) -> None:
    sf = _state_file(project_root)
    sf.write_text(state.model_dump_json(indent=2))


def init_session(project_root: Path, har_filename: str) -> SessionState:
    """Create a new autoflow session."""
    sd = _state_dir(project_root)
    sd.mkdir(parents=True, exist_ok=True)

    if _state_file(project_root).exists():
        raise ValueError("Cannot init: existing session found. Use resume or archive first.")

    session_id = f"af_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    state = SessionState(
        session_id=session_id,
        source_har=har_filename,
        current_wave=0,
        waves={
            "1": WaveState(),
            "2": WaveState(),
            "3": WaveState(),
            "4": WaveState(),
        },
    )
    _write_state(project_root, state)
    return state


def advance_wave(
    project_root: Path,
    wave: int,
    data: dict[str, Any] | None = None,
) -> SessionState:
    """Mark a wave as completed and advance."""
    state = _read_state(project_root)
    if state is None:
        raise ValueError("No session found")

    if wave != state.current_wave + 1:
        raise ValueError(f"Wave {wave} is out of order (current: {state.current_wave})")

    wave_key = str(wave)
    state.waves[wave_key] = WaveState(
        status=WaveStatus.COMPLETED,
        completed_at=_now_iso(),
        data=data or {},
    )
    state = state.model_copy(update={"current_wave": wave})
    _write_state(project_root, state)
    return state


def resume_session(project_root: Path) -> SessionState | None:
    """Resume an existing session, returns None if no session."""
    return _read_state(project_root)


def archive_session(project_root: Path) -> Path | None:
    """Archive completed session to history directory."""
    state = _read_state(project_root)
    if state is None:
        return None

    sd = _state_dir(project_root)
    history_dir = sd / "history" / state.session_id
    history_dir.mkdir(parents=True, exist_ok=True)

    # Move all files except history/
    for item in sd.iterdir():
        if item.name == "history":
            continue
        dest = history_dir / item.name
        shutil.move(str(item), str(dest))

    return history_dir
```

- [ ] **Step 4: Run all state_manager tests**

Run: `uv run pytest tests/test_state_manager.py -v`
Expected: ALL PASSED (8 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/state_manager.py tests/test_state_manager.py
git commit -m "feat: implement wave checkpoint state manager"
```

---

## Task 5: Repo Sync (TDD)

**Files:**
- Create: `scripts/repo_sync.py`
- Create: `tests/test_repo_sync.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for scripts/repo_sync.py"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from scripts.repo_sync import (
    parse_repo_url,
    load_profiles,
    sync_repo,
    sync_all,
    RepoStatus,
)


class TestParseRepoUrl:
    def test_https_url(self):
        group, name = parse_repo_url("https://git.example.com/CustomItem/dt-center-assets.git")
        assert group == "CustomItem"
        assert name == "dt-center-assets"

    def test_ssh_url(self):
        group, name = parse_repo_url("git@git.example.com:CustomItem/dt-center-assets.git")
        assert group == "CustomItem"
        assert name == "dt-center-assets"

    def test_nested_group(self):
        group, name = parse_repo_url("https://git.example.com/org/sub/repo.git")
        assert group == "org/sub"
        assert name == "repo"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_repo_url("not-a-url")


class TestLoadProfiles:
    def test_loads_yaml(self, sample_repo_profiles_path: Path):
        profiles = load_profiles(sample_repo_profiles_path)
        assert len(profiles) == 2
        assert profiles[0]["name"] == "dt-center-assets"

    def test_returns_empty_on_missing(self, tmp_path: Path):
        profiles = load_profiles(tmp_path / "missing.yaml")
        assert profiles == []


class TestSyncRepo:
    @patch("scripts.repo_sync.subprocess")
    def test_clone_new_repo(self, mock_subprocess, tmp_path: Path):
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="abc1234")
        status = sync_repo(
            repo_path=tmp_path / ".repos" / "Group" / "repo",
            repo_url="https://git.example.com/Group/repo.git",
            branch="main",
        )
        assert status.success is True
        assert mock_subprocess.run.called

    @patch("scripts.repo_sync.subprocess")
    def test_pull_existing_repo(self, mock_subprocess, tmp_path: Path):
        repo_path = tmp_path / ".repos" / "Group" / "repo"
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="abc1234")
        status = sync_repo(repo_path=repo_path, repo_url="", branch="main")
        assert status.success is True


class TestSyncAll:
    @patch("scripts.repo_sync.sync_repo")
    def test_syncs_all_profiles(self, mock_sync, sample_repo_profiles_path: Path, tmp_path: Path):
        mock_sync.return_value = RepoStatus(name="test", success=True, head_commit="abc")
        results = sync_all(sample_repo_profiles_path, tmp_path)
        assert len(results) == 2
        assert mock_sync.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_repo_sync.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement repo_sync.py**

```python
"""Git repository sync — clone, pull, checkout from repo-profiles.yaml."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RepoStatus:
    name: str
    success: bool
    head_commit: str = ""
    error: str = ""


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extract (group, repo_name) from a git URL."""
    # HTTPS: https://git.example.com/group/repo.git
    https_match = re.match(r"https?://[^/]+/(.+)/([^/]+?)(?:\.git)?$", url)
    if https_match:
        return https_match.group(1), https_match.group(2)

    # SSH: git@git.example.com:group/repo.git
    ssh_match = re.match(r"git@[^:]+:(.+)/([^/]+?)(?:\.git)?$", url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)

    raise ValueError(f"Cannot parse repo URL: {url}")


def load_profiles(profiles_path: Path) -> list[dict[str, Any]]:
    """Load repo profiles from YAML."""
    if not profiles_path.exists():
        return []
    with open(profiles_path) as f:
        config = yaml.safe_load(f)
    return config.get("profiles", [])


def sync_repo(
    repo_path: Path,
    repo_url: str = "",
    branch: str = "main",
) -> RepoStatus:
    """Clone or pull a single repository."""
    name = repo_path.name

    try:
        if (repo_path / ".git").exists():
            # Pull existing repo
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "checkout", branch],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            # Clone new repo
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "-b", branch, repo_url, str(repo_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        # Get HEAD commit
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
        )
        head = result.stdout.strip()

        return RepoStatus(name=name, success=True, head_commit=head)

    except subprocess.CalledProcessError as e:
        return RepoStatus(name=name, success=False, error=str(e.stderr or e))


def sync_all(profiles_path: Path, project_root: Path) -> list[RepoStatus]:
    """Sync all repos defined in repo-profiles.yaml."""
    profiles = load_profiles(profiles_path)
    results = []

    for profile in profiles:
        repo_path = project_root / profile["path"]
        status = sync_repo(
            repo_path=repo_path,
            repo_url=profile.get("url", ""),
            branch=profile.get("branch", "main"),
        )
        results.append(status)

    return results
```

- [ ] **Step 4: Run all repo_sync tests**

Run: `uv run pytest tests/test_repo_sync.py -v`
Expected: ALL PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/repo_sync.py tests/test_repo_sync.py
git commit -m "feat: implement repo sync with clone, pull, and URL parsing"
```

---

## Task 6: Scaffold Generator (TDD) + Templates

**Files:**
- Create: `scripts/scaffold.py`
- Create: `tests/test_scaffold.py`
- Create: `templates/pyproject.toml.j2`
- Create: `templates/conftest.py.j2`
- Create: `templates/.env.example`

- [ ] **Step 1: Create Jinja2 templates**

`templates/pyproject.toml.j2`:
```toml
[project]
name = "{{ project_name }}-tests"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.28",
    "pydantic>=2.10",
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "allure-pytest>=2.13",
    "rich>=13.9",{% if db_configured %}
    "pymysql>=1.1",{% endif %}
    "python-dotenv>=1.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "interface: API endpoint tests",
    "scenario: Business scenario tests",
    "unit: Unit tests",
    "db: Requires database connection",
]
addopts = "-v --strict-markers"

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TCH"]

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "basic"
```

`templates/conftest.py.j2`:
```python
"""Global test fixtures."""
import os

import pytest
from dotenv import load_dotenv

from core.client import APIClient
{% if db_configured %}from core.db import DBHelper{% endif %}

load_dotenv()


@pytest.fixture(scope="session")
def client() -> APIClient:
    return APIClient(
        base_url=os.getenv("BASE_URL", "{{ base_url }}"),
        headers={"Cookie": os.getenv("AUTH_COOKIE", "")},
    )


{% if db_configured %}@pytest.fixture(scope="session")
def db() -> DBHelper | None:
    db_url = os.getenv("DB_URL")
    if not db_url:
        return None
    return DBHelper(db_url)
{% else %}@pytest.fixture(scope="session")
def db() -> None:
    return None
{% endif %}
```

`templates/.env.example`:
```
BASE_URL=http://172.16.115.247
AUTH_COOKIE=SESSION=your_session_cookie_here

# Optional: Database connection
# DB_URL=mysql://user:password@host:port/database

# Optional: Notification webhooks
# DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
# FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
# SLACK_WEBHOOK=https://hooks.slack.com/services/xxx
```

- [ ] **Step 2: Write failing tests for scaffold.py**

```python
"""Tests for scripts/scaffold.py"""
from pathlib import Path

import pytest

from scripts.scaffold import generate_project, ScaffoldConfig


class TestGenerateProject:
    def test_creates_directory_structure(self, tmp_path: Path):
        config = ScaffoldConfig(
            project_root=tmp_path,
            project_name="mytest",
            base_url="http://localhost:8080",
            db_configured=False,
        )
        generate_project(config)
        assert (tmp_path / "tests" / "interface").is_dir()
        assert (tmp_path / "tests" / "scenariotest").is_dir()
        assert (tmp_path / "tests" / "unittest").is_dir()
        assert (tmp_path / "core").is_dir()
        assert (tmp_path / "core" / "models").is_dir()

    def test_creates_pyproject_toml(self, tmp_path: Path):
        config = ScaffoldConfig(
            project_root=tmp_path,
            project_name="mytest",
            base_url="http://localhost:8080",
            db_configured=False,
        )
        generate_project(config)
        content = (tmp_path / "pyproject.toml").read_text()
        assert "mytest-tests" in content
        assert "pymysql" not in content

    def test_includes_pymysql_when_db_configured(self, tmp_path: Path):
        config = ScaffoldConfig(
            project_root=tmp_path,
            project_name="mytest",
            base_url="http://localhost:8080",
            db_configured=True,
        )
        generate_project(config)
        content = (tmp_path / "pyproject.toml").read_text()
        assert "pymysql" in content

    def test_creates_conftest(self, tmp_path: Path):
        config = ScaffoldConfig(
            project_root=tmp_path,
            project_name="mytest",
            base_url="http://localhost:8080",
            db_configured=False,
        )
        generate_project(config)
        assert (tmp_path / "tests" / "conftest.py").exists()

    def test_creates_core_files(self, tmp_path: Path):
        config = ScaffoldConfig(
            project_root=tmp_path,
            project_name="mytest",
            base_url="http://localhost:8080",
            db_configured=False,
        )
        generate_project(config)
        assert (tmp_path / "core" / "__init__.py").exists()
        assert (tmp_path / "core" / "client.py").exists()
        assert (tmp_path / "core" / "assertions.py").exists()
        assert (tmp_path / "core" / "models" / "__init__.py").exists()

    def test_does_not_overwrite_existing(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("existing content")
        config = ScaffoldConfig(
            project_root=tmp_path,
            project_name="mytest",
            base_url="http://localhost:8080",
            db_configured=False,
        )
        generate_project(config)
        assert (tmp_path / "pyproject.toml").read_text() == "existing content"

    def test_creates_gitignore(self, tmp_path: Path):
        config = ScaffoldConfig(
            project_root=tmp_path,
            project_name="mytest",
            base_url="http://localhost:8080",
            db_configured=False,
        )
        generate_project(config)
        content = (tmp_path / ".gitignore").read_text()
        assert ".autoflow/" in content
        assert ".repos/" in content
        assert ".env" in content

    def test_creates_makefile(self, tmp_path: Path):
        config = ScaffoldConfig(
            project_root=tmp_path,
            project_name="mytest",
            base_url="http://localhost:8080",
            db_configured=False,
        )
        generate_project(config)
        content = (tmp_path / "Makefile").read_text()
        assert "test-all" in content
        assert "test-interface" in content
```

- [ ] **Step 3: Implement scaffold.py**

```python
"""Project scaffolding generator — creates directory structure and config files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

PLUGIN_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = PLUGIN_DIR / "templates"


@dataclass(frozen=True)
class ScaffoldConfig:
    project_root: Path
    project_name: str
    base_url: str
    db_configured: bool = False


def _write_if_not_exists(path: Path, content: str) -> bool:
    """Write file only if it doesn't exist. Returns True if written."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


def generate_project(config: ScaffoldConfig) -> list[str]:
    """Generate project scaffolding. Returns list of created files."""
    root = config.project_root
    created: list[str] = []

    # Directories
    dirs = [
        root / "tests" / "interface",
        root / "tests" / "scenariotest",
        root / "tests" / "unittest",
        root / "core" / "models",
        root / ".autoflow",
        root / ".repos",
        root / ".trash",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Jinja2 templates
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )
    template_vars = {
        "project_name": config.project_name,
        "base_url": config.base_url,
        "db_configured": config.db_configured,
    }

    template_map = {
        "pyproject.toml.j2": root / "pyproject.toml",
        "conftest.py.j2": root / "tests" / "conftest.py",
        ".env.example": root / ".env.example",
    }

    for tmpl_name, dest in template_map.items():
        try:
            tmpl = env.get_template(tmpl_name)
            content = tmpl.render(**template_vars)
        except Exception:
            # .env.example is not a Jinja2 template, just copy it
            src = TEMPLATES_DIR / tmpl_name
            content = src.read_text() if src.exists() else ""
        if _write_if_not_exists(dest, content):
            created.append(str(dest.relative_to(root)))

    # Static files
    static_files = {
        root / "core" / "__init__.py": "",
        root / "core" / "models" / "__init__.py": "",
        root / "tests" / "interface" / "__init__.py": "",
        root / "tests" / "scenariotest" / "__init__.py": "",
        root / "tests" / "unittest" / "__init__.py": "",
        root / "core" / "client.py": _CLIENT_PY,
        root / "core" / "assertions.py": _ASSERTIONS_PY,
    }

    if config.db_configured:
        static_files[root / "core" / "db.py"] = _DB_PY

    for path, content in static_files.items():
        if _write_if_not_exists(path, content):
            created.append(str(path.relative_to(root)))

    # .gitignore for user project
    gitignore = """__pycache__/
*.py[cod]
.venv/
.autoflow/
.repos/
.trash/
.env
htmlcov/
.coverage
reports/
"""
    if _write_if_not_exists(root / ".gitignore", gitignore):
        created.append(".gitignore")

    # Makefile for user project
    makefile = """.PHONY: test-all test-interface test-scenario test-unit report lint typecheck

test-all:
\tuv run pytest tests/ -v --alluredir=reports/allure-results

test-interface:
\tuv run pytest tests/interface/ -v --alluredir=reports/allure-results

test-scenario:
\tuv run pytest tests/scenariotest/ -v --alluredir=reports/allure-results

test-unit:
\tuv run pytest tests/unittest/ -v

report:
\tallure serve reports/allure-results

lint:
\tuv run ruff check .

typecheck:
\tuv run pyright
"""
    if _write_if_not_exists(root / "Makefile", makefile):
        created.append("Makefile")

    return created


_CLIENT_PY = '''"""HTTP client — immutable wrapper around httpx."""
from dataclasses import dataclass, field

import httpx


@dataclass(frozen=True)
class APIClient:
    base_url: str
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0

    def _build_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
        )

    def get(self, path: str, **kwargs) -> httpx.Response:
        with self._build_client() as c:
            return c.get(path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        with self._build_client() as c:
            return c.post(path, **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        with self._build_client() as c:
            return c.put(path, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        with self._build_client() as c:
            return c.delete(path, **kwargs)
'''

_ASSERTIONS_PY = '''"""L1-L5 assertion helpers."""
import httpx


def assert_protocol(
    response: httpx.Response,
    *,
    expected_status: int = 200,
    max_time_ms: int = 5000,
    expected_content_type: str = "application/json",
) -> None:
    """L1 Protocol layer assertion."""
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}"
    )
    elapsed_ms = response.elapsed.total_seconds() * 1000
    assert elapsed_ms <= max_time_ms, (
        f"Response too slow: {elapsed_ms:.0f}ms > {max_time_ms}ms"
    )
    content_type = response.headers.get("content-type", "")
    assert expected_content_type in content_type, (
        f"Content-Type mismatch: {content_type}"
    )
'''

_DB_PY = '''"""Database query helper — read-only, for assertion verification."""
from dataclasses import dataclass

import pymysql


@dataclass(frozen=True)
class DBHelper:
    url: str

    def _connect(self):
        # Parse mysql://user:pass@host:port/db
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return pymysql.connect(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip("/"),
            cursorclass=pymysql.cursors.DictCursor,
        )

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()
        finally:
            conn.close()

    def query_all(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()

    def count(self, table: str, where: str = "1=1", params: tuple = ()) -> int:
        result = self.query_one(f"SELECT COUNT(*) as cnt FROM {table} WHERE {where}", params)
        return result["cnt"] if result else 0
'''
```

- [ ] **Step 4: Run scaffold tests**

Run: `uv run pytest tests/test_scaffold.py -v`
Expected: ALL PASSED (8 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/scaffold.py tests/test_scaffold.py templates/
git commit -m "feat: implement scaffold generator with Jinja2 templates"
```

---

## Task 7: Notifier (TDD)

**Files:**
- Create: `scripts/notifier.py`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for scripts/notifier.py"""
from unittest.mock import patch, MagicMock

import pytest

from scripts.notifier import (
    format_dingtalk,
    format_feishu,
    format_slack,
    send_notification,
    NotificationPayload,
)


class TestFormatDingtalk:
    def test_markdown_format(self):
        payload = NotificationPayload(
            title="AutoFlow Complete",
            body="Generated 87 tests\n- Pass: 78\n- Fail: 5",
        )
        msg = format_dingtalk(payload)
        assert msg["msgtype"] == "markdown"
        assert "AutoFlow Complete" in msg["markdown"]["title"]
        assert "87 tests" in msg["markdown"]["text"]

    def test_truncates_long_body(self):
        payload = NotificationPayload(title="Test", body="x" * 10000)
        msg = format_dingtalk(payload)
        assert len(msg["markdown"]["text"]) <= 5000


class TestFormatFeishu:
    def test_card_format(self):
        payload = NotificationPayload(title="AutoFlow", body="Done")
        msg = format_feishu(payload)
        assert msg["msg_type"] == "interactive"
        assert "AutoFlow" in str(msg)


class TestFormatSlack:
    def test_blocks_format(self):
        payload = NotificationPayload(title="AutoFlow", body="Done")
        msg = format_slack(payload)
        assert "blocks" in msg
        assert any("AutoFlow" in str(b) for b in msg["blocks"])


class TestSendNotification:
    @patch("scripts.notifier.httpx")
    def test_sends_dingtalk(self, mock_httpx):
        mock_httpx.post.return_value = MagicMock(status_code=200)
        payload = NotificationPayload(title="Test", body="Body")
        result = send_notification("dingtalk", "https://webhook.example.com", payload)
        assert result is True
        mock_httpx.post.assert_called_once()

    @patch("scripts.notifier.httpx")
    def test_returns_false_on_failure(self, mock_httpx):
        mock_httpx.post.side_effect = Exception("Network error")
        payload = NotificationPayload(title="Test", body="Body")
        result = send_notification("dingtalk", "https://webhook.example.com", payload)
        assert result is False

    def test_unknown_channel_raises(self):
        payload = NotificationPayload(title="Test", body="Body")
        with pytest.raises(ValueError, match="Unknown channel"):
            send_notification("telegram", "https://example.com", payload)
```

- [ ] **Step 2: Implement notifier.py**

```python
"""External notification — webhook to DingTalk, Feishu, Slack, Custom."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

MAX_BODY_LENGTH = 4500


@dataclass(frozen=True)
class NotificationPayload:
    title: str
    body: str


def _truncate(text: str, max_len: int = MAX_BODY_LENGTH) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 20] + "\n\n... (truncated)"


def format_dingtalk(payload: NotificationPayload) -> dict:
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": payload.title,
            "text": f"## {payload.title}\n\n{_truncate(payload.body)}",
        },
    }


def format_feishu(payload: NotificationPayload) -> dict:
    return {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": payload.title}},
            "elements": [
                {"tag": "markdown", "content": _truncate(payload.body)},
            ],
        },
    }


def format_slack(payload: NotificationPayload) -> dict:
    return {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": payload.title}},
            {"type": "section", "text": {"type": "mrkdwn", "text": _truncate(payload.body)}},
        ],
    }


FORMATTERS = {
    "dingtalk": format_dingtalk,
    "feishu": format_feishu,
    "slack": format_slack,
    "custom": format_dingtalk,  # Custom uses same format as DingTalk
}


def send_notification(channel: str, webhook_url: str, payload: NotificationPayload) -> bool:
    """Send notification to a webhook. Returns True on success."""
    if channel not in FORMATTERS:
        raise ValueError(f"Unknown channel: {channel}")

    formatter = FORMATTERS[channel]
    message = formatter(payload)

    try:
        resp = httpx.post(webhook_url, json=message, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False
```

- [ ] **Step 3: Run notifier tests**

Run: `uv run pytest tests/test_notifier.py -v`
Expected: ALL PASSED (6 tests)

- [ ] **Step 4: Commit**

```bash
git add scripts/notifier.py tests/test_notifier.py
git commit -m "feat: implement webhook notifier for DingTalk, Feishu, Slack"
```

---

## Task 8: Test Runner Wrapper (TDD)

**Files:**
- Create: `scripts/test_runner.py`
- Create: `tests/test_runner_wrapper.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for scripts/test_runner.py"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from scripts.test_runner import (
    build_pytest_command,
    parse_pytest_output,
    TestResult,
    run_tests,
)


class TestBuildCommand:
    def test_basic_command(self, tmp_path: Path):
        cmd = build_pytest_command(tmp_path / "tests", collect_only=False)
        assert "pytest" in cmd[1]
        assert str(tmp_path / "tests") in cmd

    def test_collect_only(self, tmp_path: Path):
        cmd = build_pytest_command(tmp_path / "tests", collect_only=True)
        assert "--collect-only" in cmd

    def test_with_allure(self, tmp_path: Path):
        cmd = build_pytest_command(tmp_path / "tests", allure_dir=tmp_path / "results")
        assert f"--alluredir={tmp_path / 'results'}" in cmd


class TestParseOutput:
    def test_parses_passed(self):
        output = "===== 10 passed in 2.34s ====="
        result = parse_pytest_output(output, return_code=0)
        assert result.passed == 10
        assert result.failed == 0
        assert result.success is True

    def test_parses_mixed(self):
        output = "===== 8 passed, 2 failed, 1 skipped in 5.00s ====="
        result = parse_pytest_output(output, return_code=1)
        assert result.passed == 8
        assert result.failed == 2
        assert result.skipped == 1
        assert result.success is False

    def test_parses_no_tests(self):
        output = "===== no tests ran in 0.01s ====="
        result = parse_pytest_output(output, return_code=5)
        assert result.passed == 0


class TestRunTests:
    @patch("scripts.test_runner.subprocess")
    def test_returns_result(self, mock_subprocess, tmp_path: Path):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout="===== 5 passed in 1.00s =====",
            stderr="",
        )
        result = run_tests(tmp_path / "tests")
        assert result.passed == 5
        assert result.success is True
```

- [ ] **Step 2: Implement test_runner.py**

```python
"""pytest execution wrapper — command building, result parsing."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestResult:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    success: bool = False
    output: str = ""


def build_pytest_command(
    test_path: Path,
    collect_only: bool = False,
    allure_dir: Path | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build a pytest invocation command."""
    cmd = ["uv", "run", "pytest", str(test_path), "-v"]

    if collect_only:
        cmd.append("--collect-only")

    if allure_dir:
        cmd.append(f"--alluredir={allure_dir}")

    if extra_args:
        cmd.extend(extra_args)

    return cmd


def parse_pytest_output(output: str, return_code: int) -> TestResult:
    """Parse pytest summary line into structured result."""
    passed = failed = skipped = errors = 0

    # Match patterns like "10 passed", "2 failed", "1 skipped"
    for match in re.finditer(r"(\d+) (passed|failed|skipped|error)", output):
        count = int(match.group(1))
        kind = match.group(2)
        if kind == "passed":
            passed = count
        elif kind == "failed":
            failed = count
        elif kind == "skipped":
            skipped = count
        elif kind == "error":
            errors = count

    return TestResult(
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        success=return_code == 0,
        output=output,
    )


def run_tests(
    test_path: Path,
    collect_only: bool = False,
    allure_dir: Path | None = None,
    timeout: int = 300,
) -> TestResult:
    """Run pytest and return structured results."""
    cmd = build_pytest_command(test_path, collect_only=collect_only, allure_dir=allure_dir)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return parse_pytest_output(result.stdout + result.stderr, result.returncode)
    except subprocess.TimeoutExpired:
        return TestResult(success=False, output="Test execution timed out")
    except Exception as e:
        return TestResult(success=False, output=str(e))
```

- [ ] **Step 3: Run test_runner tests**

Run: `uv run pytest tests/test_runner_wrapper.py -v`
Expected: ALL PASSED (6 tests)

- [ ] **Step 4: Run full test suite + coverage**

Run: `make ci`
Expected: All lint, typecheck, and tests pass. Coverage ≥ 80% for scripts/.

- [ ] **Step 5: Commit**

```bash
git add scripts/test_runner.py tests/test_runner_wrapper.py
git commit -m "feat: implement pytest execution wrapper with result parsing"
```

---

## Task 9: Prompt Documents

**Files:**
- Create: `prompts/har-parse-rules.md`
- Create: `prompts/scenario-enrich.md`
- Create: `prompts/assertion-layers.md`
- Create: `prompts/code-style-python.md`
- Create: `prompts/review-checklist.md`

These are Markdown instruction templates read by agents. No code, no tests — but they must be precise and actionable per the spec sections 4.3-4.6 and 6.1-6.3.

- [ ] **Step 1: Create har-parse-rules.md**

Content based on spec section 4.3 har-parser agent logic. Covers:
- Keep rules (XHR/Fetch, application/json)
- Drop rules (static extensions list, WebSocket 101, noise patterns)
- Dedup strategy (same method+path+status, different params, different status codes)
- Sensitive header stripping (Cookie, Authorization, x-auth-token)

- [ ] **Step 2: Create scenario-enrich.md**

Content based on spec section 4.4 scenario generation categories. Covers:
- 8 scenario categories with source signals and examples
- CRUD closure detection logic (scan Controller for related endpoints)
- Source code analysis strategy (Controller → Service → DAO tracing)
- L1-L5 assertion planning rules per endpoint

- [ ] **Step 3: Create assertion-layers.md**

Content based on spec section 6. Covers:
- L1-L5 definitions with code patterns
- Layer-to-test-type matrix
- Generation rules per layer (what to extract from HAR, what from source)
- DB assertion rules (optional, write operations only)
- L5 provenance requirements (source file:line, confidence)

- [ ] **Step 4: Create code-style-python.md**

Content based on spec section 4.5 code generation constraints. Covers:
- File structure, naming conventions
- Assertion ordering (L1→L5)
- Pydantic model generation rules
- Immutability requirements (frozen dataclass)
- Size limits (file < 400 lines, function < 50 lines)
- Data management (API fixtures with yield cleanup)

- [ ] **Step 5: Create review-checklist.md**

Content based on spec section 4.6 review dimensions. Covers:
- Assertion completeness per layer per test type
- Scenario completeness (CRUD, exceptions, boundaries)
- Source code cross-check
- Code quality (no hardcoded, no mutation, proper cleanup)
- Runnability (imports, fixtures, conftest)
- Deviation thresholds (<15%, 15-40%, >40%)

- [ ] **Step 6: Commit**

```bash
git add prompts/
git commit -m "feat: add prompt templates for agents (parse, enrich, assert, style, review)"
```

---

## Task 10: Agent Definitions

**Files:**
- Create: `agents/har-parser.md`
- Create: `agents/repo-syncer.md`
- Create: `agents/scenario-analyzer.md`
- Create: `agents/case-writer.md`
- Create: `agents/case-reviewer.md`

Each agent file has YAML frontmatter (name, description, tools, model) and Markdown instructions. Follow spec section 5.

- [ ] **Step 1: Create har-parser.md**

Frontmatter: `name: har-parser, model: haiku, tools: Read, Bash, Write`
Instructions: Call `scripts/har_parser.py`, read `prompts/har-parse-rules.md`, output `.autoflow/parsed.json`, move HAR to `.trash/`.

- [ ] **Step 2: Create repo-syncer.md**

Frontmatter: `name: repo-syncer, model: haiku, tools: Bash, Read`
Instructions: Read `repo-profiles.yaml`, call `scripts/repo_sync.py` for each repo, output `.autoflow/repo-status.json`.

- [ ] **Step 3: Create scenario-analyzer.md**

Frontmatter: `name: scenario-analyzer, model: opus, tools: Read, Grep, Glob, Bash`
Instructions: Read parsed.json + source code, follow `prompts/scenario-enrich.md` + `prompts/assertion-layers.md`, output `.autoflow/scenarios.json` + `.autoflow/generation-plan.json`. Most detailed agent — includes full source tracing strategy from spec section 4.4.

- [ ] **Step 4: Create case-writer.md**

Frontmatter: `name: case-writer, model: sonnet, tools: Read, Grep, Glob, Write, Edit`
Instructions: Receive assigned endpoints from generation-plan.json, read source code, follow `prompts/code-style-python.md` + `prompts/assertion-layers.md`, generate test files.

- [ ] **Step 5: Create case-reviewer.md**

Frontmatter: `name: case-reviewer, model: opus, tools: Read, Grep, Glob, Write, Edit, Bash`
Instructions: Review generated code per `prompts/review-checklist.md`, auto-fix per deviation thresholds, run pytest, collect results, output `.autoflow/review-report.json` + `.autoflow/execution-report.json`.

- [ ] **Step 6: Commit**

```bash
git add agents/
git commit -m "feat: add agent definitions for all 5 pipeline agents"
```

---

## Task 11: /using-autoflow SKILL.md

**Files:**
- Create: `skills/using-autoflow/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Frontmatter from spec section 3.1. Body implements the 5-step flow from spec section 3.2 as detailed agent instructions. Key points:
- Step 1: Environment detection using Bash (python3 --version, uv --version, git --version)
- Step 2: Style detection/confirmation using AskUserQuestion
- Step 3: Repo config using AskUserQuestion + Bash (git clone)
- Step 4: Connection config using AskUserQuestion
- Step 5: Scaffold generation using Bash (python scripts/scaffold.py) + Write (CLAUDE.md)
- Must stay under 500 lines

- [ ] **Step 2: Commit**

```bash
git add skills/using-autoflow/
git commit -m "feat: add /using-autoflow initialization wizard skill"
```

---

## Task 12: /autoflow SKILL.md

**Files:**
- Create: `skills/autoflow/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Frontmatter from spec section 4.1. Body implements the four-wave orchestration from spec section 4.2-4.6:
- Pre-flight checks (environment, resume, HAR validation, argument parsing)
- Wave 1: Launch har-parser and repo-syncer agents in parallel
- Wave 2: Launch scenario-analyzer agent, present confirmation checklist via AskUserQuestion
- Wave 3: Fan out case-writer agents by module
- Wave 4: Launch case-reviewer agent, present acceptance report, send notifications
- State management: checkpoint after each wave using scripts/state_manager.py
- Resume logic: read checkpoint, skip completed waves
- Must stay under 500 lines

- [ ] **Step 2: Commit**

```bash
git add skills/autoflow/
git commit -m "feat: add /autoflow main workflow skill with four-wave orchestration"
```

---

## Task 13: README.md with Mermaid Diagrams

**Files:**
- Create: `README.md` (overwrite existing one-liner)

- [ ] **Step 1: Write README.md**

Follow spec section 12 structure exactly. Include:
- Badges (MIT license, Python 3.12+, Claude Code Plugin)
- Features section (5 bullet points from spec 12.1)
- Quick Start (install + first run)
- How It Works — embed the Mermaid workflow diagram from spec 12.2
- Assertion Layers — embed the Mermaid layer diagram from spec 12.3
- Installation (Claude Code Plugin + GitHub)
- Usage (/using-autoflow + /autoflow with examples)
- Configuration (repo-profiles.yaml schema + .env table)
- Project Structure (generated) — tree diagram from spec section 9
- Development (prerequisites, setup, make test, make lint)
- Init Flow — embed the Mermaid init diagram from spec 12.4
- Roadmap (v0.1.0 → v1.0.0 from spec 14.4)
- Contributing + License

- [ ] **Step 2: Create references/ directory**

Create `references/assertion-examples.md` and `references/tech-stack-options.md` with content summarizing the L1-L5 examples and alternative tech stacks from the brainstorming research.

- [ ] **Step 3: Commit**

```bash
git add README.md references/
git commit -m "docs: add README with Mermaid diagrams and reference docs"
```

---

## Task 14: CI/CD + Publishing Setup

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --dev
      - run: uv run ruff check scripts/ tests/
      - run: uv run ruff format --check scripts/ tests/
      - run: uv run pyright scripts/
      - run: uv run pytest tests/ -v --cov=scripts --cov-report=xml
      - uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.13'
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
```

- [ ] **Step 2: Commit**

```bash
git add .github/
git commit -m "ci: add GitHub Actions workflow for lint, typecheck, and tests"
```

---

## Task 15: Final Validation

- [ ] **Step 1: Run full CI locally**

Run: `make ci`
Expected: All lint, typecheck, and tests pass.

- [ ] **Step 2: Verify plugin structure**

Run: `find . -name "*.md" -path "*/skills/*" -o -name "*.md" -path "*/agents/*" -o -name "*.md" -path "*/prompts/*" | sort`
Expected: All 12 Markdown files present (2 skills + 5 agents + 5 prompts).

- [ ] **Step 3: Verify file count**

Run: `find . -name "*.py" -path "*/scripts/*" | wc -l`
Expected: 7 (6 scripts + __init__.py)

Run: `find . -name "test_*.py" | wc -l`
Expected: 6 test files

- [ ] **Step 4: Test coverage check**

Run: `uv run pytest tests/ --cov=scripts --cov-report=term-missing --cov-fail-under=80`
Expected: PASS — coverage ≥ 80%

- [ ] **Step 5: Create release tag**

```bash
git tag v0.1.0
```

- [ ] **Step 6: Final commit (if any remaining changes)**

```bash
git add -A && git commit -m "chore: final validation and cleanup for v0.1.0"
```
