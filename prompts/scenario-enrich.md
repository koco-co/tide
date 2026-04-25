# 场景丰富策略

> 引用方：`agents/scenario-analyzer.md`
> 用途：`scenario-analyzer` Agent 的规则，用于从 HAR 接口 + 源码分析中生成全面的测试场景。

---

## 1. 源码分析策略

对 `parsed.json` 中的每个接口，逐层追踪源码以理解完整业务逻辑，再生成场景。

### 1.1 层级追踪顺序

```
Controller 层 → Service 层 → DAO/Mapper 层
```

**第一步 — 定位 Controller 方法**

使用 `Grep` 查找与接口路径匹配的路由注解。

示例（Java Spring）：

```bash
# 搜索路由注解
grep -r "@PostMapping.*recentQuery" .repos/
grep -r "@RequestMapping.*datamap" .repos/
```

查找：`@GetMapping`、`@PostMapping`、`@PutMapping`、`@DeleteMapping`、`@RequestMapping`

**第二步 — 追踪到 Service 层**

从 Controller 方法找到 Service 调用（如 `xxxService.recentQuery()`），通过阅读 Service 接口和实现文件跟踪调用链。

从 Service 层提取的内容：

- 业务逻辑分支（`if/else`、`switch/case`）
- 权限检查（`@PreAuthorize`、`hasPermission()`、角色检查）
- 校验逻辑（超出 `@Valid` 注解范围的手动校验）
- 外部服务调用（其他微服务、Redis、MQ）
- 异常抛出模式（`throw new XxxException(...)`）
- 状态/状态机转换

**第三步 — 追踪到 DAO/Mapper 层**

从 Service 找到数据库操作，阅读 Mapper XML 或 JPA Repository。

从 DAO 层提取的内容：

- 表名和关键字段
- SQL 条件（`WHERE is_deleted = 0`、软删除模式）
- 字段约束（NOT NULL、UNIQUE、VARCHAR 长度）
- 关联表 JOIN（表明存在数据联动场景）

**第四步 — 识别同一 Controller 中的关联接口**

找到 Controller 文件后，扫描同一类中所有 `@XxxMapping` 方法。

原因：如果找到 `addDataMap`、`updateDataMap`、`deleteDataMap`、`queryDataMap`，说明这是一个完整的 CRUD 闭环组。

---

## 2. 8 种场景类别

从以下类别生成场景。每个类别描述了其在源码中的信号、示例和优先级。

---

### 类别 1：HAR 直接场景

**英文名**: HAR Direct

**含义**：HAR 文件中记录的原始请求。使用真实录制参数的"正常路径"场景。

**信号**：`parsed.json` 中 `response.status == 200` 且响应体非空的任意接口。

**场景示例**：

```
name: "query_recent_datamap_with_recorded_params"
description: "回放 HAR 中录制的查询请求，验证响应结构一致"
test_type: interface
request: <从 parsed.json 复制>
assertion_layers: [L1, L2, L3]
```

**优先级**：HIGH — 对每个接口都必须生成。

---

### 类别 2：CRUD 闭环场景

**英文名**: CRUD Closure

**含义**：创建 → 查询 → 更新 → 删除的完整生命周期测试序列。确保 API 创建的数据能被查询、修改和删除。

**源码信号**：

- 同一 Controller 类中有命名为以下动词的方法：`add/create/save` + `query/list/page/get` + `update/edit/modify` + `delete/remove`
- 常见命名模式（Java）：`add`、`update`、`delete`、`pageXxx`、`listXxx`、`getById`

**检测算法**：

```python
crud_signals = {
    "create": ["add", "create", "save", "insert"],
    "read":   ["query", "list", "page", "get", "find", "search"],
    "update": ["update", "edit", "modify", "patch"],
    "delete": ["delete", "remove", "del"],
}
# 对每个 Controller：检查是否全部 4 种 CRUD 类型都存在
```

**场景示例**：

```
name: "sync_task_full_crud_lifecycle"
description: "add → pageTask（验证创建） → update → pageTask（验证更新） → delete → pageTask（验证不存在）"
test_type: scenariotest
test_file: tests/scenariotest/dmetadata_syncTask/test_sync_task_crud.py
assertion_layers: [L1, L2, L3, L4]
```

**优先级**：HIGH — 对每个 CRUD 完整的 Controller 都必须生成。

**注意**：若 HAR 中 CRUD 不完整（如只录制了查询接口），仍需生成闭环场景——用例生成 Agent 需要从源码参数类型中推断缺失的请求体。

---

### 类别 3：参数校验场景

**英文名**: Parameter Validation

**含义**：验证 API 能正确拒绝无效或缺失输入，并返回合适错误响应。

**源码信号**：

- Controller 方法参数上的 `@Valid`、`@Validated` 注解
- DTO/VO 字段上的 `@NotNull`、`@NotBlank`、`@NotEmpty`
- 手动校验：`if (param == null) throw new ...`
- JSR-303/JSR-380 约束注解

**场景模板**（对每个有校验的接口至少生成以下场景）：

| 场景                       | 请求修改方式                | 期望状态码       |
| -------------------------- | --------------------------- | ---------------- |
| 缺少必填字段               | 删除某个 `@NotNull` 字段    | 400 或业务错误码 |
| `@NotBlank` 字段为空字符串 | 将字段设为 `""`             | 400 或业务错误码 |
| 类型错误                   | 期望整数字段传入字符串      | 400              |
| 必填对象为 null            | 将必填对象请求体设为 `null` | 400              |

**示例**：

```
name: "add_sync_task_missing_task_name"
description: "taskName 标注了 @NotNull — 不传该字段提交，期望返回错误"
test_type: interface
request: {不含 taskName 的请求体}
assertion_layers: [L1, L2]
expected: response.code != 1（或 status 400）
```

**优先级**：MEDIUM — 对有明显校验注解的接口生成。

---

### 类别 4：边界值场景

**英文名**: Boundary Values

**含义**：在有效输入范围的边界处测试——最小值、最大值和刚超出边界的值。

**源码信号**：

- 数值字段上的 `@Min(N)`、`@Max(N)`
- 字符串/集合上的 `@Size(min=N, max=M)`
- 小数字段的 `@DecimalMin`、`@DecimalMax`
- 分页参数：`pageSize`、`pageNum`、`currentPage`
- DB 列约束（VARCHAR 长度、INT 范围）

**场景模板**：

| 字段类型                      | 需生成的边界场景                                             |
| ----------------------------- | ------------------------------------------------------------ |
| 分页 `pageSize`               | `pageSize=0`、`pageSize=1`、`pageSize=100`、`pageSize=10000` |
| 分页 `pageNum`                | `pageNum=0`、`pageNum=1`                                     |
| `@Min(1) @Max(100) int level` | `level=0`、`level=1`、`level=100`、`level=101`               |
| 字符串 `@Size(max=255)`       | 255 字符字符串、256 字符字符串                               |

**示例**：

```
name: "page_task_with_zero_page_size"
description: "pageSize=0 低于最小值，应返回错误或空结果，而非 500"
test_type: interface
request: {currentPage: 1, pageSize: 0}
assertion_layers: [L1, L2]
```

**优先级**：MEDIUM — 对有数值/集合参数的接口生成。

---

### 类别 5：权限校验场景

**英文名**: Permission Check

**含义**：验证未授权用户无法访问受保护接口。

**源码信号**：

- `@PreAuthorize("hasRole('ADMIN')")` 或类似注解
- `@RequiresPermission`、`@Secured`
- 手动权限检查：`if (!user.hasPermission(xxx)) throw new UnauthorizedException()`
- Service 层中基于角色的条件逻辑

**场景模板**：

| 场景     | 模拟方式                     | 期望结果       |
| -------- | ---------------------------- | -------------- |
| 未认证   | 不带 Cookie/token 发送请求   | 401 或重定向   |
| 令牌过期 | 使用明显无效的令牌           | 401            |
| 权限不足 | 使用低权限用户令牌（如可用） | 403 或业务错误 |

**示例**：

```
name: "preview_data_without_permission"
description: "DataTableService.previewData 调用 judgeOpenDataPreviewByParam — 未认证访问应失败"
test_type: interface
annotation: "L5 AI 推断：DataTableService.java:234"
assertion_layers: [L1, L5]
confidence: HIGH
```

**优先级**：源码有权限检查时为 HIGH；无检查时为 LOW。

---

### 类别 6：状态机场景

**英文名**: State Transition

**含义**：验证实体状态转换遵循定义的状态机——合法转换成功，非法转换失败。

**源码信号**：

- 含状态值的 `Enum`：`DRAFT`、`RUNNING`、`SUCCESS`、`FAILED`、`CANCELLED`
- 状态转换方法：`startTask()`、`stopTask()`、`pauseTask()`
- 转换守卫：`if (task.status != DRAFT) throw new InvalidStateException()`
- Service 层中的状态常量

**场景模板**：

| 场景         | 测试内容                                            |
| ------------ | --------------------------------------------------- |
| 合法正向转换 | 通过 `start` API 执行 `DRAFT → RUNNING`             |
| 非法反向转换 | 尝试 `start` 一个已处于 `RUNNING` 的任务 → 期望报错 |
| 非法跳跃转换 | 尝试将 `DRAFT` 任务直接标记为 `complete` → 期望报错 |

**示例**：

```
name: "sync_task_cannot_start_when_running"
description: "SyncTaskService：RUNNING 状态的任务不能再次启动"
test_type: scenariotest
steps: [创建任务, 启动任务, 再次尝试启动]
assertion_layers: [L1, L2, L4]
```

**优先级**：源码有明确状态枚举 + 转换守卫时为 HIGH。

---

### 类别 7：关联数据联动场景

**英文名**: Related Data Linkage

**含义**：验证操作能正确级联到关联实体——删除父实体应清理子实体，或以约束错误拒绝操作。

**源码信号**：

- Service 层中的跨服务调用：`metadataService.deleteByDataMapId(id)`
- Mapper/DAO SQL JOIN 中的外键关系
- 操作多张表的方法上的 `@Transactional` 注解
- 级联逻辑："删除数据源应删除其所有同步任务"

**场景模板**：

| 场景                 | 测试内容                                          |
| -------------------- | ------------------------------------------------- |
| 删除有子记录的父记录 | 创建父记录 + 子记录 → 删除父记录 → 验证子记录状态 |
| 更新父记录影响子记录 | 更新父记录名称 → 验证子记录能看到更新后的名称     |
| 跨服务一致性         | 在服务 A 中创建 → 验证服务 B 中可见               |

**示例**：

```
name: "delete_datasource_cascades_sync_tasks"
description: "删除数据源应级联删除（或报错阻止）相关同步任务"
test_type: scenariotest
assertion_layers: [L1, L2, L4]
db_required: true
```

**优先级**：MEDIUM — 在能看到跨表或跨服务操作时生成。

---

### 类别 8：异常路径场景

**英文名**: Exception Paths

**含义**：验证 API 能优雅处理错误条件——返回有意义的错误码/消息，而非 500 错误。

**源码信号**：

- `catch` 块：`catch (DuplicateKeyException e) → return Result.fail("xxx 已存在")`
- 自定义异常类及其消息
- `throw new XxxNotFoundException(...)` 模式
- Service 层中的业务规则违反

**必须生成的最少异常场景**（对每个接口至少生成以下场景）：

| 场景       | 测试输入                             | 期望结果             |
| ---------- | ------------------------------------ | -------------------- |
| 资源不存在 | 使用不存在的 ID（如 `id=999999999`） | 业务错误码，而非 500 |
| 重复创建   | 创建相同资源两次                     | 第二次返回错误       |
| 无效引用   | 引用不存在的父级 ID                  | 校验错误             |

**示例**：

```
name: "get_nonexistent_datamap_returns_error"
description: "dataMapId=999999999 不存在 — 验证优雅报错，而非 500"
test_type: interface
request: {dataMapId: 999999999}
assertion_layers: [L1, L2]
expected: status 200, response.code != 1（或 status 404）
```

**优先级**：HIGH — 对每个接口都必须生成。"不存在"和"重复"场景是强制要求。

---

## 输出校验规则

generation_plan 必须满足以下约束：

1. **endpoint_ids 非空**：每个 worker 条目的 endpoint_ids 数组至少包含一个 ID
2. **ID 引用有效**：所有 endpoint_ids 必须能在 services[].endpoints[].id 中找到
3. **完全覆盖**：services 中每个 endpoint 至少被分配给一个 worker
4. **HAR 场景完整**：每个 endpoint 至少有一个 `har_direct` 类型的基础场景

若校验失败，必须修复后再写出 scenarios.json。

---

## 3. CRUD 闭环检测算法

使用此算法查找 CRUD 闭环组：

```python
# 对 parsed.json 中每个 service/module 组合：
#   收集同一 Controller 下的所有接口
#   检查哪些 CRUD 类型存在

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
    return found  # 包含全部 4 个键 = 完整闭环
```

扫描源码时，使用 `Grep` 在 Controller 文件中查找所有 `@XxxMapping` 注解：

```bash
grep -n "@PostMapping\|@GetMapping\|@PutMapping\|@DeleteMapping\|@RequestMapping" \
  .repos/group/repo/src/main/java/.../controller/DataMapController.java
```

---

## 4. 场景归组为测试类型

生成所有场景后，将每个场景分配到正确的测试类型：

| 测试类型       | 目录                                   | 存放内容                                                       |
| -------------- | -------------------------------------- | -------------------------------------------------------------- |
| `interface`    | `tests/interface/{service_module}/`    | 单接口测试：HAR 直接场景、参数校验、边界值、权限检查、异常路径 |
| `scenariotest` | `tests/scenariotest/{service_module}/` | 多步骤测试：CRUD 闭环、状态转换、关联数据联动                  |
| `unittest`     | `tests/unittest/{module}/`             | 业务逻辑单元测试：校验器、工具函数、纯函数（非 API 调用）      |

**命名规则**：

- 接口测试文件：`test_{module}.py`（如 `test_datamap.py`）
- 场景测试文件：`test_{module}_crud.py` 或 `test_{module}_{flow_name}.py`
- 单元测试文件：`test_{class_name}.py`

---

## 5. 各场景的断言规划

对每个生成的场景，指定适用的断言层（Assertion Layer）。将此作为 `assertion-layers.md` 的输入。

| 场景类别     | L1   | L2   | L3   | L4   | L5       |
| ------------ | ---- | ---- | ---- | ---- | -------- |
| HAR 直接场景 | 必须 | 必须 | 必须 | 可选 | 可选     |
| CRUD 闭环    | 必须 | 必须 | 必须 | 必须 | 必须     |
| 参数校验     | 必须 | 必须 | 可选 | —    | —        |
| 边界值       | 必须 | 必须 | 必须 | —    | 可选     |
| 权限校验     | 必须 | 必须 | —    | 可选 | 高置信度 |
| 状态转换     | 必须 | 必须 | 必须 | 必须 | 可选     |
| 关联数据联动 | 必须 | 必须 | —    | 必须 | 可选     |
| 异常路径     | 必须 | 必须 | 可选 | 可选 | —        |

---

## 6. 输出：scenarios.json 结构

分析并经用户确认后，写入 `.tide/scenarios.json`：

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
        "read": "POST /dmetadata/v1/syncTask/pageTask",
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
