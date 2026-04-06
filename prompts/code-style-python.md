# Python Test Code Style Guide

> Referenced by: `agents/case-writer.md`
> Purpose: Code generation rules for the `case-writer` agent. Every generated test file MUST conform to these rules.

---

## 1. File Structure

Every generated test file follows this top-to-bottom order — no exceptions:

```python
"""Module docstring: what this file tests.

Tests for: POST /dassets/v1/datamap/recentQuery
Source: dt-center-assets / DataMapController.java
"""
# 1. Standard library imports
import re
from dataclasses import dataclass

# 2. Third-party imports (alphabetical within section)
import allure
import pytest
from pydantic import BaseModel

# 3. Internal imports
from core.assertions import assert_protocol
from core.client import APIClient

# 4. Constants (module-level, UPPER_SNAKE_CASE)
VALID_META_TYPES = {1, 4, 5, 6, 7, 10}  # From MetaTypeEnum
BUSINESS_SUCCESS_CODE = 1

# 5. Pydantic response models (before test classes)
class DataItem(BaseModel):
    type: int
    count: int

class AssetStatisticsResponse(BaseModel):
    code: int
    message: str | None = None
    data: list[DataItem]
    success: bool

# 6. Test classes with allure decorators
@allure.epic("dassets")
@allure.feature("datamap")
class TestDatamapAssetStatistics:
    ...
```

---

## 2. Naming Conventions

### 2.1 File Names

```
test_{module}.py
```

Examples:
- `test_datamap.py` — tests for `/dassets/v1/datamap/` endpoints
- `test_sync_task.py` — tests for `/dmetadata/v1/syncTask/` endpoints
- `test_sync_task_crud.py` — CRUD closure tests for syncTask

### 2.2 Class Names

```
Test{Module}{Feature}
```

Examples:
- `TestDatamapRecentQuery` — tests for the `recentQuery` endpoint
- `TestDatamapAssetStatistics` — tests for the `assetStatistics` endpoint
- `TestSyncTaskCRUD` — CRUD lifecycle tests for syncTask

### 2.3 Method Names

```
test_{feature}_{scenario}
```

Examples:
- `test_recent_query_with_recorded_params` — HAR direct scenario
- `test_recent_query_missing_required_field` — parameter validation
- `test_asset_statistics_returns_valid_types` — L3 enum validation
- `test_sync_task_crud_lifecycle` — CRUD closure scenario

### 2.4 Model Names

```
{EndpointName}Response       # Top-level response model
{FieldName}Item              # Item in a list
{FieldName}Page              # Paginated wrapper
```

Examples:
- `AssetStatisticsResponse`, `AssetStatisticsItem`
- `PageTaskResponse`, `PageData`, `TaskItem`

---

## 3. Allure Decorator Hierarchy

Apply allure decorators in this order on every test class and method:

```python
@allure.epic("service_name")          # e.g., "dassets", "dmetadata"
@allure.feature("module_name")        # e.g., "datamap", "syncTask"
class TestModuleFeature:

    @allure.story("scenario_category")  # e.g., "har_direct", "crud_closure"
    @allure.title("Human-readable test title")
    @allure.severity(allure.severity_level.CRITICAL)  # BLOCKER/CRITICAL/NORMAL/MINOR/TRIVIAL
    def test_feature_scenario(self, client: APIClient) -> None:
        ...
```

**Severity mapping**:
| Scenario category | Severity |
|-------------------|----------|
| CRUD closure | `CRITICAL` |
| HAR direct (happy path) | `CRITICAL` |
| Permission check | `CRITICAL` |
| Parameter validation | `NORMAL` |
| Boundary values | `NORMAL` |
| State transition | `CRITICAL` |
| Related data linkage | `CRITICAL` |
| Exception paths | `NORMAL` |

---

## 4. Assertion Ordering

Within each test method, ALWAYS assert in this order: L1 → L2 → L3 → L4 → L5.

```python
def test_asset_statistics_success(self, client: APIClient) -> None:
    # Arrange
    payload = {"type": 1}

    # Act
    resp = client.post("/dassets/v1/datamap/assetStatistics", json=payload)

    # L1 — Protocol
    assert_protocol(resp, expected_status=200, max_time_ms=360)

    # L2 — Structure
    body = AssetStatisticsResponse.model_validate(resp.json())

    # L3 — Data
    assert body.code == BUSINESS_SUCCESS_CODE
    for item in body.data:
        assert item.type in VALID_META_TYPES, f"Invalid meta type: {item.type}"
        assert item.count >= 0

    # L4 — Business (only in scenariotest or when explicitly planned)
    # (omit for interface tests unless specifically required)

    # L5 — AI-inferred (only when planned, with required comment)
    # (omit unless this scenario has planned L5 assertions)
```

**Do not intermix layers** — all L1 assertions before all L2, all L2 before all L3, etc.

---

## 5. L2 — Pydantic Model Usage

Always use `model_validate()` for L2 structural assertions — never manually check field presence.

```python
# CORRECT: model_validate raises ValidationError if structure is wrong
body = AssetStatisticsResponse.model_validate(resp.json())

# WRONG: manual field checks are fragile and verbose
data = resp.json()
assert "code" in data
assert "data" in data
assert isinstance(data["data"], list)
```

**Pydantic model placement**: Define models as module-level classes above the test class, never inside test methods.

**Optional fields**: Use `field: Type | None = None` for fields that may be absent. Do NOT use `Optional[Type]` — use the union syntax.

---

## 6. L5 — AI-Inferred Assertion Requirements

Every L5 assertion block MUST have a comment immediately above it containing:
1. `L5[CONFIDENCE]:` label
2. Source file path relative to `.repos/`
3. Line number
4. One-sentence rationale

```python
# L5[HIGH]: DataTableService.java:234 — previewData() calls judgeOpenDataPreviewByParam()
# which rejects requests for non-existent or unauthorized tables.
assert resp.json()["code"] != BUSINESS_SUCCESS_CODE, (
    "Non-existent tableId should be rejected by permission check"
)
```

Never generate L5 assertions without this comment. If you cannot identify the source location, set confidence to `SPECULATIVE` and note the limitation.

---

## 7. Data Management — API Fixtures

Use pytest fixtures with `yield` for test data created via API. Never write directly to the database.

### 7.1 Module-scoped fixture for expensive setup

```python
@pytest.fixture(scope="module")
def created_task_id(client: APIClient) -> Generator[int, None, None]:
    """Create a sync task for the module, clean up after all tests."""
    resp = client.post("/dmetadata/v1/syncTask/add", json={
        "taskName": "autoflow_test_task",
        "datasourceId": 1,
    })
    task_id = resp.json()["data"]
    yield task_id
    # Cleanup — always runs even if tests fail
    client.post("/dmetadata/v1/syncTask/delete", json={"id": task_id})
```

### 7.2 Function-scoped fixture for isolated tests

```python
@pytest.fixture
def fresh_task(client: APIClient) -> Generator[dict, None, None]:
    """Create a fresh task for each test, delete after."""
    resp = client.post("/dmetadata/v1/syncTask/add", json={
        "taskName": f"autoflow_test_{id(object())}",  # unique name
    })
    task = resp.json()["data"]
    yield task
    client.post("/dmetadata/v1/syncTask/delete", json={"id": task["id"]})
```

### 7.3 Rules for fixture data

- Use `autoflow_test_` prefix for all test-created data names — makes cleanup easy
- Use `scope="module"` for read-only fixtures (querying existing data)
- Use `scope="function"` for write fixtures (created + mutated per test)
- Never share mutable fixture state between tests
- Always clean up: `yield` + cleanup code, or `pytest.fixture(autouse=True)` cleanup

---

## 8. Immutability Rules

**Frozen dataclasses for all value objects** — never create mutable classes for test data.

```python
# CORRECT: frozen=True prevents mutation
@dataclass(frozen=True)
class QueryParams:
    current_page: int = 1
    page_size: int = 10
    keyword: str = ""

# WRONG: mutable class that could be accidentally modified
class QueryParams:
    def __init__(self):
        self.current_page = 1
```

**Never mutate fixture objects**:

```python
# WRONG: mutating a fixture
def test_update_task(self, created_task: dict) -> None:
    created_task["name"] = "new_name"  # MUTATION!

# CORRECT: create new dict
def test_update_task(self, created_task: dict) -> None:
    update_payload = {**created_task, "taskName": "new_name"}  # new object
```

---

## 9. Size Limits

| Unit | Limit | Action if exceeded |
|------|-------|--------------------|
| File | 400 lines | Split by endpoint group or scenario category |
| Test method | 50 lines | Extract steps into helper methods or fixtures |
| Fixture | 30 lines | Extract setup logic into helper functions |
| Nesting depth | 4 levels | Flatten with early returns or helper methods |

**How to split a file that exceeds 400 lines**:

```
# Before (too large):
tests/interface/dassets_datamap/test_datamap.py   # 650 lines

# After (split by endpoint):
tests/interface/dassets_datamap/test_datamap_query.py    # recent_query + asset_statistics
tests/interface/dassets_datamap/test_datamap_manage.py   # add + update + delete
```

---

## 10. Prohibited Patterns

The following patterns are NEVER allowed in generated test code:

### 10.1 No hardcoded values

```python
# WRONG: hardcoded
assert body.data[0].type == 1

# CORRECT: named constant
ASSET_TYPE_TABLE = 1
assert body.data[0].type == ASSET_TYPE_TABLE
```

Exception: test-specific IDs (like `999999999` for "non-existent") are allowed with a comment.

### 10.2 No print statements

```python
# WRONG
print(f"Response: {resp.json()}")

# CORRECT: use allure.attach for debugging info
allure.attach(str(resp.json()), name="response_body", attachment_type=allure.attachment_type.JSON)
```

### 10.3 No deep nesting

```python
# WRONG: 5+ levels of nesting
def test_complex(self, client):
    if condition1:
        for item in items:
            if condition2:
                for sub in item.subs:
                    if condition3:
                        assert sub.value == 1  # level 5

# CORRECT: flatten with early returns and helpers
def test_complex(self, client):
    items = self._get_filtered_items(client, condition1)
    for item in items:
        valid_subs = [s for s in item.subs if condition2 and condition3]
        for sub in valid_subs:
            assert sub.value == 1

def _get_filtered_items(self, client, condition):
    resp = client.post(...)
    return [i for i in resp.json()["data"] if condition]
```

### 10.4 No mutation of shared state

```python
# WRONG: modifying a shared fixture dict
def test_a(self, shared_data: dict) -> None:
    shared_data["key"] = "new_value"  # affects other tests!

# CORRECT: create new objects
def test_a(self, shared_data: dict) -> None:
    local_data = {**shared_data, "key": "new_value"}
```

### 10.5 No direct DB writes

```python
# WRONG: inserting test data directly
def test_with_db_data(self, db: DBHelper) -> None:
    db.execute("INSERT INTO sync_task ...")  # No write methods exist on DBHelper

# CORRECT: create data via API
def test_with_api_data(self, client: APIClient) -> None:
    resp = client.post("/dmetadata/v1/syncTask/add", json={...})
    task_id = resp.json()["data"]
```

`DBHelper` has only read-only methods: `query_one`, `query_all`, `count`.

---

## 11. Import Guidelines

```python
# Standard library — no alias
from pathlib import Path
from dataclasses import dataclass
from typing import Generator

# Third-party — no alias except for well-known ones
import allure
import pytest
from pydantic import BaseModel

# Internal — explicit, never wildcard
from core.assertions import assert_protocol
from core.client import APIClient
from core.db import DBHelper
```

Never use `from module import *`.

---

## 12. Type Annotations

All function signatures MUST have type annotations:

```python
# CORRECT
def test_query_success(self, client: APIClient, db: DBHelper | None) -> None:
    ...

@pytest.fixture
def task_id(self, client: APIClient) -> Generator[int, None, None]:
    ...

# WRONG: missing annotations
def test_query_success(self, client, db):
    ...
```

---

## 13. Quick Checklist Before Completing a File

- [ ] File starts with module docstring
- [ ] All imports are organized (stdlib → third-party → internal)
- [ ] All constants are defined at module level with names
- [ ] All Pydantic models are defined before test classes
- [ ] Every test class has `@allure.epic`, `@allure.feature` decorators
- [ ] Every test method has `@allure.story`, `@allure.title`, `@allure.severity`
- [ ] Assertions are in order: L1 → L2 → L3 → L4 → L5
- [ ] L2 uses `model_validate()` only
- [ ] L5 assertions have `L5[CONFIDENCE]: source:line rationale` comment
- [ ] All fixtures use `yield` with cleanup
- [ ] No `print()` statements
- [ ] No hardcoded values (except documented exception IDs)
- [ ] No mutation of shared objects
- [ ] File is under 400 lines
- [ ] All test methods are under 50 lines
- [ ] All functions have type annotations
