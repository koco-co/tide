# Assertion Layers (L1-L5)

> Referenced by: `agents/scenario-analyzer.md`, `agents/case-writer.md`
> Purpose: Generation rules for each assertion layer. Apply in order L1 → L2 → L3 → L4 → L5 within each test.

---

## Layer-to-Test-Type Matrix

This matrix is the primary contract. Agents MUST follow it without exception.

```
              L1      L2      L3      L4      L5
interface/    MUST    MUST    MUST    OPT     OPT
scenariotest/ MUST    MUST    MUST    MUST    MUST
unittest/     —       —       MUST    MUST    OPT
```

Legend:
- `MUST` — Always generate these assertions for this test type
- `OPT`  — Generate when source code provides sufficient signal
- `—`    — Not applicable for this test type

---

## L1 — Protocol Layer

**What it validates**: HTTP-level correctness — status code, response time, Content-Type.

**Generated from**: HAR response metadata (`response.status`, `response.time_ms`, `response.headers`).

### Generation Rules

| Assertion | Source | Formula |
|-----------|--------|---------|
| `status_code` | `response.status` from HAR | Use exact value from HAR |
| `max_time_ms` | `response.time_ms` from HAR | `max(har_time_ms × 3, 1000)` — minimum 1000ms |
| `content_type` | Response `Content-Type` header | Exact value from HAR, typically `"application/json"` |

### Code Pattern

```python
# Use the reusable helper in core/assertions.py
assert_protocol(
    response,
    expected_status=200,          # from HAR response.status
    max_time_ms=1000,             # max(har_time_ms × 3, 1000)
    expected_content_type="application/json",
)
```

`assert_protocol` implementation (already in `core/assertions.py`):
```python
def assert_protocol(
    response: httpx.Response,
    *,
    expected_status: int = 200,
    max_time_ms: int = 5000,
    expected_content_type: str = "application/json",
) -> None:
    assert response.status_code == expected_status
    assert response.elapsed.total_seconds() * 1000 <= max_time_ms
    assert expected_content_type in response.headers.get("content-type", "")
```

### Special Cases

- For error scenario tests (expected status 400, 404, etc.): set `expected_status` to the expected error status.
- For scenarios that expect any non-200 business error returned as HTTP 200: still assert `expected_status=200`, then check business code in L3.

---

## L2 — Structure Layer

**What it validates**: JSON response body structure — field presence, types, required vs. optional.

**Generated from**: HAR response body (infer types) + source DTO/VO class (confirm required fields and types).

### Generation Rules

1. **Create a Pydantic model for the response body.**

   Infer field types from the HAR response body JSON:

   | JSON value | Pydantic type |
   |-----------|---------------|
   | `"string"` | `str` |
   | `123` | `int` |
   | `1.23` | `float` |
   | `true/false` | `bool` |
   | `null` + present sometimes | `T \| None = None` |
   | `[]` (empty list) | `list[SubModel]` or `list[Any]` |
   | `{}` (object) | nested `BaseModel` subclass |

2. **Cross-reference source DTO/VO.**

   If source code is available, find the response DTO/VO class. Use annotations to refine the model:

   | Source annotation | Pydantic equivalent |
   |-------------------|---------------------|
   | `@NotNull` | Required field (no default) |
   | No `@NotNull` | Optional: `field: Type \| None = None` |
   | `@NotBlank String` | `str` (required) |

3. **Nested objects → nested Pydantic models.**

   Do not use `dict` for nested objects — always create a named `BaseModel` subclass.

   ```python
   # WRONG
   class QueryResponse(BaseModel):
       data: dict  # too loose

   # CORRECT
   class DataItem(BaseModel):
       type: int
       count: int

   class QueryResponse(BaseModel):
       code: int
       message: str | None = None
       data: list[DataItem]
       success: bool
   ```

4. **Lists of homogeneous objects → `list[SubModel]`.**

   If the response `data` field is a paginated result, create a model for the page wrapper:

   ```python
   class PageData(BaseModel):
       data: list[TaskItem]
       totalCount: int
       currentPage: int | None = None
       pageSize: int | None = None

   class PageTaskResponse(BaseModel):
       code: int
       message: str | None = None
       data: PageData
       success: bool
   ```

### Code Pattern

```python
# Define model above the test class
class AssetStatisticsItem(BaseModel):
    type: int
    count: int

class AssetStatisticsResponse(BaseModel):
    code: int
    message: str | None = None
    data: list[AssetStatisticsItem]
    success: bool

# In the test method:
body = AssetStatisticsResponse.model_validate(response.json())
# model_validate() raises ValidationError on structure mismatch — that IS the L2 assertion
```

**Do not add redundant `assert` statements for field existence** — `model_validate()` already verifies structure.

---

## L3 — Data Layer

**What it validates**: Value correctness — enums, ranges, formats, business codes, pagination invariants.

**Generated from**: Source Enum/constant classes, `@Min`/`@Max` annotations, field naming conventions, pagination parameters.

### Generation Rules by Data Type

#### 3.1 Enum Values

Source: Java `Enum` class or constant interface.

```java
// Source: MetaTypeEnum.java
public enum MetaTypeEnum {
    TABLE(1), VIEW(4), FOLDER(5), DATASOURCE(6), SCHEMA(7), DATABASE(10);
    private final int value;
}
```

Generated assertion:
```python
VALID_META_TYPES = {1, 4, 5, 6, 7, 10}  # From MetaTypeEnum — define as module constant
for item in body.data:
    assert item.type in VALID_META_TYPES, f"Invalid meta type: {item.type}"
```

#### 3.2 Numeric Ranges

Source: `@Min(N)`, `@Max(N)`, DB column constraints, or business rules in source.

```python
# From @Min(0) on count field
assert item.count >= 0, f"Count cannot be negative: {item.count}"

# From pageSize validation in source (1 <= pageSize <= 100)
assert 1 <= body.data.pageSize <= 100
assert body.data.totalCount >= 0
```

#### 3.3 Business Response Code

If the API uses a business `code` field (e.g., `code: 1` for success, `code: 0` for failure):

```python
# Assert success code on happy-path tests
BUSINESS_SUCCESS_CODES = {1}  # From source constants — adjust per project
assert body.code in BUSINESS_SUCCESS_CODES, f"Business error: code={body.code}, message={body.message}"
```

For error scenario tests: assert `body.code != 1` or specific error code.

#### 3.4 Format Validation

Infer from field naming conventions:

| Field name pattern | Validation |
|-------------------|------------|
| `phone`, `mobile`, `phoneNo` | `re.match(r"^1[3-9]\d{9}$", value)` |
| `email` | `re.match(r"[^@]+@[^@]+\.[^@]+", value)` |
| `createTime`, `updateTime` | `datetime.fromisoformat(value)` or timestamp integer |
| `gmtCreate`, `gmtModified` | timestamp integer `> 0` |

Only generate format assertions when the field is **non-null in the HAR response body**.

#### 3.5 Pagination Invariants

Apply to any endpoint returning paginated data:

```python
assert body.data.totalCount >= 0
assert len(body.data.data) <= body.data.pageSize if hasattr(body.data, "pageSize") else True
# Consistency check: if totalCount == 0, data list should be empty
if body.data.totalCount == 0:
    assert len(body.data.data) == 0
```

---

## L4 — Business Layer

**What it validates**: Business rule consistency, state machine correctness, CRUD data integrity, DB state (when configured).

**Generated from**: Source business logic, state machine enums, Service layer conditional branches, DAO/Mapper SQL.

### 4.1 State Machine Assertions

Source: Status enum + transition guards in Service layer.

```python
# After creating a task: verify initial status
task = next(t for t in body.data.data if t["id"] == created_task_id)
assert task["status"] == 0, "New task should have status DRAFT (0)"  # From SyncTaskStatusEnum

# After starting: verify status changed
start_resp = client.post("/dmetadata/v1/syncTask/start", json={"id": task_id})
assert start_resp.json()["code"] == 1
page_resp = client.post("/dmetadata/v1/syncTask/pageTask", json={"currentPage": 1, "pageSize": 10})
task = next(t for t in page_resp.json()["data"]["data"] if t["id"] == task_id)
assert task["status"] == 1, "Started task should have status RUNNING (1)"
```

### 4.2 CRUD Data Integrity Assertions

For CRUD closure tests, verify via API after each write operation:

```python
# add → verify created
add_resp = client.post("/dmetadata/v1/syncTask/add", json={...})
task_id = add_resp.json()["data"]

page_resp = client.post("/dmetadata/v1/syncTask/pageTask", json={"currentPage": 1, "pageSize": 100})
tasks = page_resp.json()["data"]["data"]
created_task = next((t for t in tasks if t["id"] == task_id), None)
assert created_task is not None, "Created task should appear in list"
assert created_task["taskName"] == expected_name

# update → verify changed
update_resp = client.post("/dmetadata/v1/syncTask/update", json={"id": task_id, "taskName": "new_name"})
assert update_resp.json()["code"] == 1
# Re-query and verify
...

# delete → verify absent
delete_resp = client.post("/dmetadata/v1/syncTask/delete", json={"id": task_id})
assert delete_resp.json()["code"] == 1
# Re-query: task_id should not appear
...
```

### 4.3 DB Assertions (Optional — when `db` fixture is not None)

Only generate DB assertions for **write operations** (add, update, delete).

**Detection**: Check if DAO/Mapper SQL reveals the table name and key fields.

```python
# After add: verify record exists in DB
if db:
    record = db.query_one("SELECT * FROM sync_task WHERE id = %s", (task_id,))
    assert record is not None, "Record should exist in DB after add"
    assert record["is_deleted"] == 0, "New record should not be soft-deleted"
    assert record["task_name"] == expected_name

# After delete: verify soft-deleted
if db:
    record = db.query_one("SELECT * FROM sync_task WHERE id = %s", (task_id,))
    # Soft delete: record exists with is_deleted = 1
    assert record is not None
    assert record["is_deleted"] == 1, "Deleted record should be soft-deleted"
```

**DB assertion rules**:
- `add` → verify record exists, field values match
- `update` → verify changed fields updated, verify untouched fields unchanged
- `delete` → if soft delete pattern detected (`is_deleted` field), verify `is_deleted=1`; if hard delete, verify record absent
- Wrap ALL DB assertions in `if db:` guard — DB is optional

### 4.4 Idempotency Assertions

Generate for endpoints that should be idempotent (e.g., `PUT` operations, status transitions):

```python
# Run the same update twice — second call should succeed or be a no-op
second_resp = client.post("/dmetadata/v1/syncTask/update", json={"id": task_id, "taskName": "same_name"})
assert second_resp.json()["code"] == 1, "Idempotent update should succeed on repeat"
```

---

## L5 — AI-Inferred Layer

**What it validates**: Implicit rules not expressed in annotations or obvious business logic — security boundaries, hidden limits, undocumented dependencies, implicit state constraints.

**Generated from**: Deep source code analysis — reading implementation details, comments, edge case handling.

### Mandatory Requirements for Every L5 Assertion

Every L5 assertion MUST include a comment with:
1. Source file path and line number
2. Inference rationale (what you read that suggested this rule)
3. Confidence level: `HIGH` or `SPECULATIVE`

```python
def test_preview_data_implicit_permission(self, client: APIClient) -> None:
    """
    L5 AI-inferred: DataTableService.previewData() calls judgeOpenDataPreviewByParam()
    before returning data. Non-existent or unauthorized tableId should return error code.
    Source: .repos/group/dt-center-assets/src/.../DataTableService.java:234
    Confidence: HIGH
    """
    resp = client.post("/dassets/v1/dataTable/previewData", json={"tableId": 999999999})
    assert resp.json()["code"] != 1, (
        "L5[HIGH]: Non-existent tableId should trigger permission/existence check"
    )
```

### L5 Inference Types

Generate L5 assertions for these patterns when found in source code:

| Type | Signal in source | Example assertion |
|------|-----------------|-------------------|
| **Implicit permission** | `judgeXxx()` or `checkXxx()` called before main logic | Non-admin user gets error |
| **Hidden quantity limit** | `if (count >= MAX_XXX)` in Service | Cannot create more than N items |
| **Implicit dependency** | Service checks existence of related entity before operating | Operation fails if parent deleted |
| **Implicit state constraint** | Status checked without explicit annotation | Cannot update a published record |
| **Security boundary** | Sensitive data filtered in Service before returning | Response never contains passwords/tokens |

### Confidence Levels

- `HIGH`: The source code contains an explicit check that directly implies the rule. The inference is unambiguous.
- `SPECULATIVE`: The rule is inferred from patterns, naming conventions, or partial evidence. Mark clearly.

```python
# HIGH confidence: explicit check found
# Source: UserService.java:89 — `if (!currentUser.getId().equals(resource.getOwnerId())) throw new ForbiddenException()`
assert resp.json()["code"] != 1  # L5[HIGH]: non-owner cannot modify

# SPECULATIVE: inferred from naming pattern only
# Source: DataMapService.java — method named "checkDataMapAccess" called before query, body not read
assert resp.json()["code"] != 1  # L5[SPECULATIVE]: likely access check based on method name
```

**Do not generate SPECULATIVE assertions in `interface/` tests** — only HIGH confidence for interface tests. All confidence levels are allowed in `scenariotest/`.

---

## Summary: What to Generate Per Layer

| Layer | Input | Output |
|-------|-------|--------|
| L1 | HAR `response.status`, `time_ms`, `Content-Type` header | `assert_protocol(response, ...)` call |
| L2 | HAR response body JSON + source DTO/VO | Pydantic `BaseModel` + `model_validate(response.json())` |
| L3 | Source enums, `@Min`/`@Max`, field names, pagination | `assert value in (...)`, range checks, format regex |
| L4 | Source business logic, state machine, DAO SQL | Multi-step API assertions, optional `if db:` DB checks |
| L5 | Deep source code reading, method names, comments | Commented assertions with `source:line` + confidence |
