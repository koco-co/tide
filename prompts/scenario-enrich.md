# Scenario Enrichment Strategy

> Referenced by: `agents/scenario-analyzer.md`
> Purpose: Rules for the `scenario-analyzer` agent to generate comprehensive test scenarios from HAR endpoints + source code analysis.

---

## 1. Source Code Analysis Strategy

For each endpoint in `parsed.json`, trace through the source code layer by layer to understand the full business logic before generating scenarios.

### 1.1 Layer Tracing Order

```
Controller Layer → Service Layer → DAO/Mapper Layer
```

**Step 1 — Locate the Controller method**

Use `Grep` to find the route annotation matching the endpoint path.

Examples (Java Spring):
```bash
# Search for the route annotation
grep -r "@PostMapping.*recentQuery" .repos/
grep -r "@RequestMapping.*datamap" .repos/
```

Look for: `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@RequestMapping`

**Step 2 — Trace to Service layer**

From the Controller method, identify the Service call (e.g., `xxxService.recentQuery()`). Follow the call chain by reading the Service interface and implementation files.

What to extract from the Service layer:
- Business logic branches (`if/else`, `switch/case`)
- Permission checks (`@PreAuthorize`, `hasPermission()`, role checks)
- Validation logic (beyond `@Valid` annotations)
- External service calls (other microservices, Redis, MQ)
- Exception throwing patterns (`throw new XxxException(...)`)
- Status/state machine transitions

**Step 3 — Trace to DAO/Mapper layer**

From the Service, identify database operations. Read the Mapper XML or JPA repository.

What to extract from the DAO layer:
- Table names and key fields
- SQL conditions (`WHERE is_deleted = 0`, soft delete patterns)
- Field constraints (NOT NULL, UNIQUE, VARCHAR length)
- Related table joins (indicates data linkage scenarios)

**Step 4 — Identify related endpoints in the same Controller**

After finding the Controller file, scan it for all `@XxxMapping` methods in the same class.

Why: If you find `addDataMap`, `updateDataMap`, `deleteDataMap`, `queryDataMap` — that's a CRUD closure group.

---

## 2. The 8 Scenario Categories

Generate scenarios from these categories. Each category is described with its signal in source code, an example, and its priority.

---

### Category 1: HAR Direct
**中文名**: HAR直接场景

**What it is**: The exact request recorded in the HAR file. The "happy path" with real recorded parameters.

**Signal**: Any endpoint in `parsed.json` with `response.status == 200` and a non-empty response body.

**Example scenario**:
```
name: "query_recent_datamap_with_recorded_params"
description: "Replay the exact query recorded in HAR — verify same response structure"
test_type: interface
request: <copy from parsed.json>
assertion_layers: [L1, L2, L3]
```

**Priority**: HIGH — always generate for every endpoint.

---

### Category 2: CRUD Closure
**中文名**: CRUD闭环场景

**What it is**: A sequence of create → read → update → delete operations that form a complete lifecycle test. Ensures data created by the API can also be queried, modified, and deleted.

**Signal in source code**:
- Same Controller class has methods named: `add/create/save` + `query/list/page/get` + `update/edit/modify` + `delete/remove`
- Common naming patterns (Java): `add`, `update`, `delete`, `pageXxx`, `listXxx`, `getById`

**Detection algorithm**:
```python
crud_signals = {
    "create": ["add", "create", "save", "insert"],
    "read":   ["query", "list", "page", "get", "find", "search"],
    "update": ["update", "edit", "modify", "patch"],
    "delete": ["delete", "remove", "del"],
}
# For each controller: check if all 4 CRUD types are present
```

**Example scenario**:
```
name: "sync_task_full_crud_lifecycle"
description: "add → pageTask (verify created) → update → pageTask (verify updated) → delete → pageTask (verify absent)"
test_type: scenariotest
test_file: tests/scenariotest/dmetadata_syncTask/test_sync_task_crud.py
assertion_layers: [L1, L2, L3, L4]
```

**Priority**: HIGH — generate for every CRUD-complete Controller.

**Note**: When CRUD is incomplete in HAR (e.g., only query endpoints recorded), still generate the closure scenario — the case-writer will need to synthesize the missing request bodies from source code parameter types.

---

### Category 3: Parameter Validation
**中文名**: 参数校验场景

**What it is**: Tests that verify the API rejects invalid or missing inputs with appropriate error responses.

**Signal in source code**:
- `@Valid`, `@Validated` annotations on Controller method parameters
- `@NotNull`, `@NotBlank`, `@NotEmpty` on DTO/VO fields
- Manual validation: `if (param == null) throw new ...`
- JSR-303/JSR-380 constraint annotations

**Scenario templates** (generate at least these for each validated endpoint):

| Scenario | Request modification | Expected status |
|----------|---------------------|-----------------|
| Missing required field | Remove a `@NotNull` field | 400 or business error code |
| Empty string for `@NotBlank` | Set field to `""` | 400 or business error code |
| Wrong type | Send string where int expected | 400 |
| Null required object | Set required object body to `null` | 400 |

**Example**:
```
name: "add_sync_task_missing_task_name"
description: "taskName is @NotNull — submit without it, expect error"
test_type: interface
request: {body without taskName}
assertion_layers: [L1, L2]
expected: response.code != 1 (or status 400)
```

**Priority**: MEDIUM — generate for endpoints with visible validation annotations.

---

### Category 4: Boundary Values
**中文名**: 边界值场景

**What it is**: Tests at the edges of valid input ranges — minimum, maximum, and just-outside values.

**Signal in source code**:
- `@Min(N)`, `@Max(N)` on numeric fields
- `@Size(min=N, max=M)` on strings/collections
- `@DecimalMin`, `@DecimalMax` for decimal fields
- Pagination parameters: `pageSize`, `pageNum`, `currentPage`
- DB column constraints (VARCHAR length, INT range)

**Scenario templates**:

| Field type | Boundary scenarios to generate |
|------------|-------------------------------|
| Pagination `pageSize` | `pageSize=0`, `pageSize=1`, `pageSize=100`, `pageSize=10000` |
| Pagination `pageNum` | `pageNum=0`, `pageNum=1` |
| `@Min(1) @Max(100) int level` | `level=0`, `level=1`, `level=100`, `level=101` |
| String `@Size(max=255)` | 255-char string, 256-char string |

**Example**:
```
name: "page_task_with_zero_page_size"
description: "pageSize=0 is below minimum — should return error or empty, not 500"
test_type: interface
request: {currentPage: 1, pageSize: 0}
assertion_layers: [L1, L2]
```

**Priority**: MEDIUM — generate for endpoints with numeric/collection parameters.

---

### Category 5: Permission Check
**中文名**: 权限校验场景

**What it is**: Tests that verify unauthorized users cannot access protected endpoints.

**Signal in source code**:
- `@PreAuthorize("hasRole('ADMIN')")` or similar
- `@RequiresPermission`, `@Secured`
- Manual permission check: `if (!user.hasPermission(xxx)) throw new UnauthorizedException()`
- Role-based conditional logic in Service layer

**Scenario templates**:

| Scenario | How to simulate | Expected |
|----------|-----------------|----------|
| No authentication | Send request without Cookie/token | 401 or redirect |
| Expired token | Use an obviously invalid token | 401 |
| Insufficient role | Use a token for lower-privilege user (if available) | 403 or business error |

**Example**:
```
name: "preview_data_without_permission"
description: "DataTableService.previewData checks judgeOpenDataPreviewByParam — unauthenticated access should fail"
test_type: interface
annotation: "L5 AI-inferred: DataTableService.java:234"
assertion_layers: [L1, L5]
confidence: HIGH
```

**Priority**: HIGH when source code shows permission checks. LOW when no checks are visible.

---

### Category 6: State Transition
**中文名**: 状态机场景

**What it is**: Tests that verify entity status transitions follow the defined state machine — valid transitions succeed, invalid ones fail.

**Signal in source code**:
- `Enum` with status values: `DRAFT`, `RUNNING`, `SUCCESS`, `FAILED`, `CANCELLED`
- State transition methods: `startTask()`, `stopTask()`, `pauseTask()`
- Guards on transitions: `if (task.status != DRAFT) throw new InvalidStateException()`
- Status constants in Service layer

**Scenario templates**:

| Scenario | Test |
|----------|------|
| Valid forward transition | `DRAFT → RUNNING` via `start` API |
| Invalid backward transition | Try to `start` an already `RUNNING` task → expect error |
| Invalid any→complete skip | Try to `complete` a `DRAFT` task → expect error |

**Example**:
```
name: "sync_task_cannot_start_when_running"
description: "SyncTaskService: task in RUNNING status cannot be started again"
test_type: scenariotest
steps: [create task, start task, try to start again]
assertion_layers: [L1, L2, L4]
```

**Priority**: HIGH when source code has explicit state enum + transition guards.

---

### Category 7: Related Data Linkage
**中文名**: 关联数据联动场景

**What it is**: Tests that verify operations cascade correctly across related entities — deleting a parent should clean up children, or fail with a constraint error.

**Signal in source code**:
- Cross-service calls in Service layer: `metadataService.deleteByDataMapId(id)`
- Foreign key relationships in Mapper/DAO SQL joins
- `@Transactional` annotations on operations that touch multiple tables
- Cascade logic: "delete datasource should delete all its sync tasks"

**Scenario templates**:

| Scenario | Test |
|----------|------|
| Delete parent with children | Create parent + children → delete parent → verify children state |
| Update parent affects children | Update parent name → verify children see updated name |
| Cross-service consistency | Create in service A → verify visible in service B |

**Example**:
```
name: "delete_datasource_cascades_sync_tasks"
description: "Deleting a datasource should cascade delete (or block with error) related sync tasks"
test_type: scenariotest
assertion_layers: [L1, L2, L4]
db_required: true
```

**Priority**: MEDIUM — generate when cross-table or cross-service operations are visible.

---

### Category 8: Exception Paths
**中文名**: 异常路径场景

**What it is**: Tests that verify the API handles error conditions gracefully — returns meaningful error codes/messages, not 500 errors.

**Signal in source code**:
- `catch` blocks: `catch (DuplicateKeyException e) → return Result.fail("xxx already exists")`
- Custom exception classes and their messages
- `throw new XxxNotFoundException(...)` patterns
- Business rule violations in Service

**Minimum required exception scenarios** (generate at least these for every endpoint):

| Scenario | Test input | Expected |
|----------|------------|----------|
| Resource not found | Use non-existent ID (e.g., `id=999999999`) | Business error code, not 500 |
| Duplicate create | Create the same resource twice | Error on second attempt |
| Invalid reference | Reference a non-existent parent ID | Validation error |

**Example**:
```
name: "get_nonexistent_datamap_returns_error"
description: "dataMapId=999999999 does not exist — verify graceful error, not 500"
test_type: interface
request: {dataMapId: 999999999}
assertion_layers: [L1, L2]
expected: status 200, response.code != 1 (or status 404)
```

**Priority**: HIGH — generate for every endpoint. "Not found" and "duplicate" are mandatory.

---

## 3. CRUD Closure Detection Algorithm

Use this algorithm to find CRUD closure groups:

```python
# For each service/module combination in parsed.json endpoints:
#   Collect all endpoints under the same Controller
#   Check which CRUD types are present

CRUD_VERBS = {
    "create": ["add", "create", "save", "insert", "new"],
    "read":   ["query", "list", "page", "get", "find", "search", "detail"],
    "update": ["update", "edit", "modify", "change", "set"],
    "delete": ["delete", "remove", "del", "drop"],
}

def detect_crud_closure(controller_methods: list[str]) -> dict:
    found = {}
    for method_name in controller_methods:
        name_lower = method_name.lower()
        for crud_type, verbs in CRUD_VERBS.items():
            if any(verb in name_lower for verb in verbs):
                found[crud_type] = method_name
    return found  # Has all 4 keys = complete closure
```

When scanning source code, use `Grep` to find all `@XxxMapping` annotations in the Controller file:

```bash
grep -n "@PostMapping\|@GetMapping\|@PutMapping\|@DeleteMapping\|@RequestMapping" \
  .repos/group/repo/src/main/java/.../controller/DataMapController.java
```

---

## 4. Scenario Grouping into Test Types

After generating all scenarios, assign each to the correct test type:

| Test Type | Directory | What goes here |
|-----------|-----------|----------------|
| `interface` | `tests/interface/{service_module}/` | Single-endpoint tests: HAR direct, parameter validation, boundary values, permission checks, exception paths |
| `scenariotest` | `tests/scenariotest/{service_module}/` | Multi-step tests: CRUD closures, state transitions, related data linkage |
| `unittest` | `tests/unittest/{module}/` | Business logic unit tests: validators, helpers, pure functions (not API calls) |

**Naming rules**:
- Interface test file: `test_{module}.py` (e.g., `test_datamap.py`)
- Scenario test file: `test_{module}_crud.py` or `test_{module}_{flow_name}.py`
- Unit test file: `test_{class_name}.py`

---

## 5. Assertion Planning per Scenario

For each generated scenario, specify which assertion layers apply. Use this as input to `assertion-layers.md`.

| Scenario Category | L1 | L2 | L3 | L4 | L5 |
|-------------------|----|----|----|----|----|
| HAR direct | MUST | MUST | MUST | OPT | OPT |
| CRUD closure | MUST | MUST | MUST | MUST | MUST |
| Parameter validation | MUST | MUST | OPT | — | — |
| Boundary values | MUST | MUST | MUST | — | OPT |
| Permission check | MUST | MUST | — | OPT | HIGH |
| State transition | MUST | MUST | MUST | MUST | OPT |
| Related data linkage | MUST | MUST | — | MUST | OPT |
| Exception paths | MUST | MUST | OPT | OPT | — |

---

## 6. Output: scenarios.json Structure

After analysis and user confirmation, write `.autoflow/scenarios.json`:

```json
{
  "total_scenarios": 87,
  "by_category": {
    "har_direct": 27,
    "crud_closure": 9,
    "parameter_validation": 18,
    "boundary_values": 12,
    "permission_check": 5,
    "state_transition": 6,
    "related_data_linkage": 4,
    "exception_paths": 6
  },
  "by_test_type": {
    "interface": 60,
    "scenariotest": 18,
    "unittest": 9
  },
  "crud_groups": [
    {
      "module": "syncTask",
      "controller": "SyncTaskController",
      "endpoints": {
        "create": "POST /dmetadata/v1/syncTask/add",
        "read":   "POST /dmetadata/v1/syncTask/pageTask",
        "update": "POST /dmetadata/v1/syncTask/update",
        "delete": "POST /dmetadata/v1/syncTask/delete"
      }
    }
  ],
  "scenarios": [
    {
      "id": "sc_001",
      "category": "har_direct",
      "name": "query_recent_datamap_with_recorded_params",
      "endpoint_id": "ep_001",
      "test_type": "interface",
      "test_file": "tests/interface/dassets_datamap/test_datamap.py",
      "assertion_layers": ["L1", "L2", "L3"],
      "priority": "HIGH",
      "source_ref": null
    }
  ]
}
```
