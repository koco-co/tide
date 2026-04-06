# Case Review Checklist

> Referenced by: `agents/case-reviewer.md`
> Purpose: Review criteria and auto-correction thresholds for the `case-reviewer` agent.

---

## How to Use This Checklist

1. Read every generated test file in the assigned scope.
2. For each check below, record: `PASS`, `FAIL`, or `N/A`.
3. Count total `FAIL` items and calculate the deviation rate.
4. Apply the correction action based on the deviation threshold (§6).
5. Output a structured `review-report.json` after review.

---

## 1. Assertion Completeness

Verify that each test file has the correct assertion layers per the Layer-to-Test-Type Matrix.

```
              L1      L2      L3      L4      L5
interface/    MUST    MUST    MUST    OPT     OPT
scenariotest/ MUST    MUST    MUST    MUST    MUST
unittest/     —       —       MUST    MUST    OPT
```

### 1.1 L1 Protocol Assertions — MUST for interface/ and scenariotest/

| Check | What to verify |
|-------|---------------|
| `assert_protocol()` called | Every test method in interface/ and scenariotest/ calls `assert_protocol()` from `core/assertions.py` |
| `expected_status` matches HAR | The `expected_status` argument matches the HAR `response.status` for that endpoint |
| `max_time_ms` is reasonable | Value is `max(har_time_ms × 3, 1000)` — not hardcoded to an arbitrary value |
| Content-Type present | `expected_content_type` is set and matches the HAR response Content-Type |

### 1.2 L2 Structure Assertions — MUST for interface/ and scenariotest/

| Check | What to verify |
|-------|---------------|
| Pydantic model exists | A `BaseModel` subclass is defined for each response type |
| `model_validate()` called | Every test uses `model_validate(resp.json())`, not manual field checks |
| Nested objects modeled | No `dict` types for nested JSON objects — should be `BaseModel` subclasses |
| Optional fields correct | Fields that can be `null` in HAR are `Type \| None = None`, not required |

### 1.3 L3 Data Assertions — MUST for all test types that have L3

| Check | What to verify |
|-------|---------------|
| Enum validations present | If source has Enum/constants, there are `assert value in (...)` checks |
| Business code checked | `assert body.code == BUSINESS_SUCCESS_CODE` on success scenarios |
| Range checks present | `@Min`/`@Max` fields have range assertions |
| Pagination invariants | Paginated responses have `totalCount >= 0`, list length consistency checks |
| Named constants used | Enum values use module-level constants, not inline integers |

### 1.4 L4 Business Assertions — MUST for scenariotest/

| Check | What to verify |
|-------|---------------|
| CRUD steps verify data | After `add`: re-query and verify item appears. After `update`: re-query and verify changed. After `delete`: re-query and verify absent |
| State transitions verified | Status field is checked at each step of a state machine flow |
| DB assertions guarded | All `if db:` DB assertion blocks exist where planned — and are properly guarded |
| No DB writes | `DBHelper` is only called for `query_one`, `query_all`, `count` — never `execute` or `insert` |

### 1.5 L5 AI-Inferred Assertions — MUST for scenariotest/, HIGH confidence only for interface/

| Check | What to verify |
|-------|---------------|
| Source comment present | Every L5 assertion has `# L5[CONFIDENCE]: source_file:line — rationale` above it |
| Confidence labeled | `HIGH` or `SPECULATIVE` is explicitly stated in the comment |
| SPECULATIVE excluded from interface/ | No `SPECULATIVE` confidence assertions in `tests/interface/` files |
| Rationale is specific | The comment names a specific method, condition, or code pattern — not vague |

---

## 2. Scenario Completeness

Verify that the generated scenarios cover the required categories from `scenarios.json`.

### 2.1 CRUD Closure Completeness

For each CRUD group identified in `scenarios.json`:

| Check | What to verify |
|-------|---------------|
| All 4 CRUD operations tested | create + read + update + delete steps all present in the CRUD test |
| Verification steps present | After each write, the test re-queries to verify the change |
| Cleanup in fixture | Created data is cleaned up via `yield` fixture, even on test failure |
| Correct test type | CRUD closure tests are in `tests/scenariotest/`, not `tests/interface/` |

### 2.2 Exception Path Coverage

Every endpoint MUST have AT LEAST these exception scenarios:

| Required exception scenario | What to check |
|-----------------------------|---------------|
| Resource not found | A test with a non-existent ID (e.g., `id=999999999`) |
| Permission denied (when source has auth checks) | A test with invalid/missing authentication |

Additional exception scenarios from `scenarios.json` must also be present.

### 2.3 Boundary Value Coverage

For endpoints with numeric parameters:

| Check | What to verify |
|-------|---------------|
| Zero/negative values tested | `pageSize=0`, negative IDs, etc. |
| Maximum values tested | Large `pageSize`, large IDs |
| Boundary at constraint edge | Values at exactly `@Min` and `@Max` |

### 2.4 Parameter Validation Coverage

For endpoints with `@Valid`/`@NotNull` fields:

| Check | What to verify |
|-------|---------------|
| Missing required field test | At least one test removes a required field |
| Empty string test | At least one test sends `""` for a `@NotBlank` field |

---

## 3. Source Code Cross-Check

After reviewing generated tests, do a quick source code scan to catch missed scenarios.

### 3.1 Controller Method Coverage

```bash
# Find all @XxxMapping methods in the Controller
grep -n "@PostMapping\|@GetMapping\|@PutMapping\|@DeleteMapping" \
  .repos/group/repo/src/main/java/.../controller/DataMapController.java
```

Check: Is every Controller method referenced by at least one test? If a method has no corresponding test, flag it.

### 3.2 Exception Handler Coverage

```bash
# Find all exception throws in the Service
grep -n "throw new\|return Result.fail\|return R.error" \
  .repos/group/repo/src/main/java/.../service/DataMapService.java
```

Check: For each distinct exception/error return in the Service, is there a test that triggers it?

### 3.3 Conditional Branch Coverage

```bash
# Find if/else branches in the Service
grep -n "if (" .repos/group/repo/src/main/java/.../service/DataMapService.java | head -20
```

Check: Are there major business branches (not trivial null checks) that have no corresponding test scenario? Flag these as gaps.

---

## 4. Code Quality Checks

### 4.1 No Hardcoded Values

| Check | What to look for |
|-------|-----------------|
| No inline magic numbers | No raw integers like `1`, `4`, `5` in assertions without named constants |
| No inline URLs | No hardcoded base URLs in test methods — should use `client` fixture |
| No inline credentials | No cookies, tokens, or passwords in test code |

Exception: Non-existent IDs (`999999999`) are allowed with a comment.

### 4.2 No Mutation

| Check | What to look for |
|-------|-----------------|
| No fixture mutation | Test methods never modify fixture objects directly |
| Frozen dataclasses used | Any custom value objects use `@dataclass(frozen=True)` |
| No shared mutable state | No module-level mutable variables modified across tests |

### 4.3 Proper Cleanup

| Check | What to look for |
|-------|-----------------|
| API fixtures use `yield` | Every fixture that creates data via API has cleanup code after `yield` |
| Cleanup uses API | Cleanup uses `client.delete/post` — not direct DB operations |
| `scope` is appropriate | Read-only fixtures use `scope="module"`, write fixtures use `scope="function"` |

### 4.4 Size Limits

| Check | Limit | How to verify |
|-------|-------|---------------|
| File length | < 400 lines | `wc -l` on each generated file |
| Test method length | < 50 lines | Count lines in each `def test_` method |
| Nesting depth | ≤ 4 levels | Check for deeply nested `for`/`if` blocks |

Files exceeding 400 lines must be split by endpoint group or scenario category.

### 4.5 Type Annotations

| Check | What to look for |
|-------|-----------------|
| All test methods annotated | `def test_xxx(self, client: APIClient) -> None:` |
| All fixtures annotated | `def fixture_xxx(...) -> Generator[T, None, None]:` |
| No bare `dict` or `list` | Use `dict[str, Any]` or `list[SubModel]` |

---

## 5. Runnability Checks

### 5.1 Import Completeness

| Check | What to verify |
|-------|---------------|
| All used symbols imported | No `NameError` would occur — all names are imported or defined |
| No circular imports | Internal imports don't create cycles |
| `allure` imported | `import allure` present if allure decorators used |
| `pytest` imported | `import pytest` present if fixtures or marks used |

### 5.2 Fixture Availability

| Check | What to verify |
|-------|---------------|
| `client` fixture used correctly | `client: APIClient` parameter available from `tests/conftest.py` |
| `db` fixture used correctly | `db: DBHelper \| None` parameter available from `tests/conftest.py` |
| Module-local fixtures defined | Any fixture used in the file is either defined in the file, its `conftest.py`, or `tests/conftest.py` |
| No fixture name collisions | No fixture with same name redefined at multiple levels |

### 5.3 Syntax and Collection

Run the following check as part of runnability verification:

```bash
uv run pytest --collect-only tests/
```

Expected: All test files collected without errors. Any `SyntaxError`, `ImportError`, or `FixtureLookupError` is a **blocking issue** — fix before marking review complete.

---

## 6. Deviation Thresholds and Correction Actions

Calculate the deviation rate after completing all checks:

```
deviation_rate = (number of FAIL items) / (total applicable checks) × 100%
```

| Deviation Rate | Action |
|----------------|--------|
| **< 15%** | **Silent fix** — correct issues directly using `Edit` tool, no user notification required |
| **15% – 40%** | **Fix and flag** — correct all issues, then add a `flag_items` section to `review-report.json` listing what was changed and why |
| **> 40%** | **Block and escalate** — do NOT auto-fix, write a detailed `review-report.json` describing all issues, notify user via AskUserQuestion, request guidance before proceeding |

### When to use AskUserQuestion

Use `AskUserQuestion` for:
- Deviation > 40% (always)
- Ambiguous source code that could be interpreted multiple ways for L4/L5 assertions
- Missing source code that prevents scenario generation for a planned test
- Test execution failures that cannot be fixed after 2 auto-fix rounds

---

## 7. Review Report Output

After completing the review, write `.autoflow/review-report.json`:

```json
{
  "reviewed_at": "<ISO8601>",
  "files_reviewed": ["tests/interface/dassets_datamap/test_datamap.py"],
  "total_checks": 42,
  "passed": 38,
  "failed": 4,
  "deviation_rate": 9.5,
  "action_taken": "silent_fix",
  "issues_found": [
    {
      "file": "tests/interface/dassets_datamap/test_datamap.py",
      "check": "L1 Protocol Assertions",
      "line": 45,
      "severity": "MEDIUM",
      "description": "max_time_ms hardcoded to 5000 instead of calculated from HAR time (45ms × 3 = 135ms, min 1000ms)",
      "fixed": true
    }
  ],
  "flag_items": [],
  "blocking_issues": []
}
```

Severity levels for issues:
- `CRITICAL`: Assertion is completely missing (MUST layer not implemented)
- `HIGH`: Assertion logic is wrong (wrong expected value, wrong method)
- `MEDIUM`: Assertion is suboptimal (hardcoded, missing constants, not immutable)
- `LOW`: Style issue (naming, missing annotation)
