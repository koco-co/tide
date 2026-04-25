# 断言层（Assertion Layers）L1-L5

> 引用方：`agents/scenario-analyzer.md`、`agents/case-writer.md`
> 用途：每个断言层的生成规则。在每个测试中按 L1 → L2 → L3 → L4 → L5 的顺序应用。

---

## 断言层与测试类型矩阵

此矩阵是主要规范，Agent 必须严格遵守，不得例外。

```
              L1      L2      L3      L4      L5
interface/    必须    必须    必须    可选    可选
scenariotest/ 必须    必须    必须    必须    必须
unittest/     —       —       必须    必须    可选
```

图例：

- `必须` — 该测试类型必须始终生成这些断言
- `可选` — 当源码提供足够信号时生成
- `—` — 该测试类型不适用

---

## L1 — 协议层（Protocol Layer）

**验证内容**：HTTP 层面的正确性——状态码、响应时间、Content-Type。

**生成来源**：HAR 响应元数据（`response.status`、`response.time_ms`、`response.headers`）。

### 生成规则

| 断言           | 来源                       | 公式                                             |
| -------------- | -------------------------- | ------------------------------------------------ |
| `status_code`  | HAR 的 `response.status`   | 使用 HAR 中的精确值                              |
| `max_time_ms`  | HAR 的 `response.time_ms`  | `max(har_time_ms × 3, 1000)` — 最小 1000ms       |
| `content_type` | 响应 `Content-Type` 请求头 | 使用 HAR 中的精确值，通常为 `"application/json"` |

### 代码模式

```python
# 使用 core/assertions.py 中的可复用辅助函数
assert_protocol(
    response,
    expected_status=200,          # 来自 HAR response.status
    max_time_ms=1000,             # max(har_time_ms × 3, 1000)
    expected_content_type="application/json",
)
```

`assert_protocol` 实现（已在 `core/assertions.py` 中）：

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

### 特殊情况

- 错误场景测试（期望状态码为 400、404 等）：将 `expected_status` 设为对应的错误状态码。
- 期望 HTTP 200 返回业务错误的场景：仍断言 `expected_status=200`，然后在 L3 中检查业务码。

---

## L2 — 结构层（Structure Layer）

**验证内容**：JSON 响应体结构——字段是否存在、类型是否正确、必填与可选字段。

**生成来源**：HAR 响应体（推断类型）+ 源码 DTO/VO 类（确认必填字段和类型）。

### 生成规则

1. **为响应体创建 Pydantic 模型。**

   从 HAR 响应体 JSON 推断字段类型：

   | JSON 值           | Pydantic 类型                   |
   | ----------------- | ------------------------------- |
   | `"string"`        | `str`                           |
   | `123`             | `int`                           |
   | `1.23`            | `float`                         |
   | `true/false`      | `bool`                          |
   | `null` + 有时存在 | `T \| None = None`              |
   | `[]`（空列表）    | `list[SubModel]` 或 `list[Any]` |
   | `{}`（对象）      | 嵌套 `BaseModel` 子类           |

2. **与源码 DTO/VO 交叉验证。**

   若有源码，找到响应 DTO/VO 类，利用注解精化模型：

   | 源码注解           | Pydantic 等价写法                  |
   | ------------------ | ---------------------------------- |
   | `@NotNull`         | 必填字段（无默认值）               |
   | 无 `@NotNull`      | 可选：`field: Type \| None = None` |
   | `@NotBlank String` | `str`（必填）                      |

3. **嵌套对象 → 嵌套 Pydantic 模型。**

   嵌套对象不能使用 `dict`，必须创建命名的 `BaseModel` 子类。

   ```python
   # 错误写法
   class QueryResponse(BaseModel):
       data: dict  # 过于宽松

   # 正确写法
   class DataItem(BaseModel):
       type: int
       count: int

   class QueryResponse(BaseModel):
       code: int
       message: str | None = None
       data: list[DataItem]
       success: bool
   ```

4. **同类型对象列表 → `list[SubModel]`。**

   若响应 `data` 字段是分页结果，为分页包装创建专用模型：

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

### 代码模式

```python
# 在测试类上方定义模型
class AssetStatisticsItem(BaseModel):
    type: int
    count: int

class AssetStatisticsResponse(BaseModel):
    code: int
    message: str | None = None
    data: list[AssetStatisticsItem]
    success: bool

# 在测试方法中：
body = AssetStatisticsResponse.model_validate(response.json())
# model_validate() 在结构不匹配时会抛出 ValidationError — 这本身就是 L2 断言
```

**不要添加多余的字段存在性 `assert` 语句** — `model_validate()` 已经验证了结构。

---

## L3 — 数据层（Data Layer）

**验证内容**：值的正确性——枚举值、范围、格式、业务码、分页不变量。

**生成来源**：源码枚举/常量类、`@Min`/`@Max` 注解、字段命名约定、分页参数。

### 各数据类型的生成规则

#### 3.1 枚举值

来源：Java `Enum` 类或常量接口。

```java
// 来源：MetaTypeEnum.java
public enum MetaTypeEnum {
    TABLE(1), VIEW(4), FOLDER(5), DATASOURCE(6), SCHEMA(7), DATABASE(10);
    private final int value;
}
```

生成的断言：

```python
VALID_META_TYPES = {1, 4, 5, 6, 7, 10}  # 来自 MetaTypeEnum — 定义为模块级常量
for item in body.data:
    assert item.type in VALID_META_TYPES, f"无效的 meta 类型：{item.type}"
```

#### 3.2 数值范围

来源：`@Min(N)`、`@Max(N)`、DB 列约束或源码中的业务规则。

```python
# 来自 count 字段的 @Min(0)
assert item.count >= 0, f"count 不能为负数：{item.count}"

# 来自源码中的 pageSize 校验（1 <= pageSize <= 100）
assert 1 <= body.data.pageSize <= 100
assert body.data.totalCount >= 0
```

#### 3.3 业务响应码

若 API 使用业务 `code` 字段（如 `code: 1` 表示成功，`code: 0` 表示失败）：

```python
# 在正常路径测试中断言成功码
BUSINESS_SUCCESS_CODES = {1}  # 来自源码常量 — 根据项目调整
assert body.code in BUSINESS_SUCCESS_CODES, f"业务错误：code={body.code}, message={body.message}"
```

错误场景测试：断言 `body.code != 1` 或具体的错误码。

#### 3.4 格式校验

从字段命名约定推断：

| 字段名模式                   | 校验方式                                     |
| ---------------------------- | -------------------------------------------- |
| `phone`、`mobile`、`phoneNo` | `re.match(r"^1[3-9]\d{9}$", value)`          |
| `email`                      | `re.match(r"[^@]+@[^@]+\.[^@]+", value)`     |
| `createTime`、`updateTime`   | `datetime.fromisoformat(value)` 或整数时间戳 |
| `gmtCreate`、`gmtModified`   | 整数时间戳 `> 0`                             |

仅在字段在 **HAR 响应体中非空时**才生成格式断言。

#### 3.5 分页不变量

适用于返回分页数据的任何接口：

```python
assert body.data.totalCount >= 0
assert len(body.data.data) <= body.data.pageSize if hasattr(body.data, "pageSize") else True
# 一致性检查：若 totalCount == 0，数据列表应为空
if body.data.totalCount == 0:
    assert len(body.data.data) == 0
```

---

## L4 — 业务层（Business Layer）

**验证内容**：业务规则一致性、状态机正确性、CRUD 数据完整性、DB 状态（配置时）。

**生成来源**：源码业务逻辑、状态机枚举、Service 层条件分支、DAO/Mapper SQL。

### 4.1 状态机断言

来源：状态枚举 + Service 层中的转换守卫。

```python
# 创建任务后：验证初始状态
task = next(t for t in body.data.data if t["id"] == created_task_id)
assert task["status"] == 0, "新任务应处于 DRAFT 状态（0）"  # 来自 SyncTaskStatusEnum

# 启动后：验证状态变更
start_resp = client.post("/dmetadata/v1/syncTask/start", json={"id": task_id})
assert start_resp.json()["code"] == 1
page_resp = client.post("/dmetadata/v1/syncTask/pageTask", json={"currentPage": 1, "pageSize": 10})
task = next(t for t in page_resp.json()["data"]["data"] if t["id"] == task_id)
assert task["status"] == 1, "已启动的任务应处于 RUNNING 状态（1）"
```

### 4.2 CRUD 数据完整性断言

CRUD 闭环测试中，在每次写操作后通过 API 验证：

```python
# add → 验证已创建
add_resp = client.post("/dmetadata/v1/syncTask/add", json={...})
task_id = add_resp.json()["data"]

page_resp = client.post("/dmetadata/v1/syncTask/pageTask", json={"currentPage": 1, "pageSize": 100})
tasks = page_resp.json()["data"]["data"]
created_task = next((t for t in tasks if t["id"] == task_id), None)
assert created_task is not None, "创建的任务应出现在列表中"
assert created_task["taskName"] == expected_name

# update → 验证已更新
update_resp = client.post("/dmetadata/v1/syncTask/update", json={"id": task_id, "taskName": "new_name"})
assert update_resp.json()["code"] == 1
# 重新查询并验证
...

# delete → 验证已不存在
delete_resp = client.post("/dmetadata/v1/syncTask/delete", json={"id": task_id})
assert delete_resp.json()["code"] == 1
# 重新查询：task_id 应不再出现
...
```

### 4.3 DB 断言（可选 — 当 `db` fixture 非 None 时）

仅对**写操作**（add、update、delete）生成 DB 断言。

**检测**：查看 DAO/Mapper SQL 是否揭示了表名和关键字段。

```python
# add 后：验证 DB 中存在记录
if db:
    record = db.query_one("SELECT * FROM sync_task WHERE id = %s", (task_id,))
    assert record is not None, "add 后 DB 中应存在记录"
    assert record["is_deleted"] == 0, "新记录不应被软删除"
    assert record["task_name"] == expected_name

# delete 后：验证软删除
if db:
    record = db.query_one("SELECT * FROM sync_task WHERE id = %s", (task_id,))
    # 软删除：记录存在但 is_deleted = 1
    assert record is not None
    assert record["is_deleted"] == 1, "删除的记录应被软删除"
```

**DB 断言规则**：

- `add` → 验证记录存在，字段值匹配
- `update` → 验证变更字段已更新，未修改字段保持不变
- `delete` → 若检测到软删除模式（`is_deleted` 字段），验证 `is_deleted=1`；若硬删除，验证记录不存在
- 所有 DB 断言必须包裹在 `if db:` 守卫中 — DB 是可选的

### 4.4 幂等性断言

对应该幂等的接口生成（如 `PUT` 操作、状态转换）：

```python
# 执行相同更新两次 — 第二次调用应成功或为无操作
second_resp = client.post("/dmetadata/v1/syncTask/update", json={"id": task_id, "taskName": "same_name"})
assert second_resp.json()["code"] == 1, "幂等更新重复执行应成功"
```

---

## L5 — AI 推断层（AI-Inferred Layer）

**验证内容**：注解或明显业务逻辑中未表达的隐式规则——安全边界、隐藏限制、未文档化的依赖关系、隐式状态约束。

**生成来源**：深度源码分析——阅读实现细节、注释、边缘情况处理。

### 每条 L5 断言的强制要求

每条 L5 断言必须包含如下注释：

1. 源文件路径和行号
2. 推断依据（你读到了什么，促使你得出此规则）
3. 置信度：`HIGH`（高置信度）或 `SPECULATIVE`（推测性）

```python
def test_preview_data_implicit_permission(self, client: APIClient) -> None:
    """
    L5 AI 推断：DataTableService.previewData() 在返回数据前调用了 judgeOpenDataPreviewByParam()。
    不存在或未授权的 tableId 应返回错误码。
    来源：.repos/group/dt-center-assets/src/.../DataTableService.java:234
    置信度：HIGH
    """
    resp = client.post("/dassets/v1/dataTable/previewData", json={"tableId": 999999999})
    assert resp.json()["code"] != 1, (
        "L5[HIGH]：不存在的 tableId 应触发权限/存在性检查"
    )
```

### L5 推断类型

在源码中发现以下模式时生成 L5 断言：

| 类型             | 源码信号                                    | 示例断言                  |
| ---------------- | ------------------------------------------- | ------------------------- |
| **隐式权限**     | 主逻辑前调用了 `judgeXxx()` 或 `checkXxx()` | 非管理员用户收到错误      |
| **隐藏数量限制** | Service 中有 `if (count >= MAX_XXX)`        | 无法创建超过 N 条记录     |
| **隐式依赖**     | Service 在操作前检查关联实体是否存在        | 父记录被删除后操作失败    |
| **隐式状态约束** | 无显式注解的状态检查                        | 已发布记录不能更新        |
| **安全边界**     | Service 在返回前过滤敏感数据                | 响应中永远不包含密码/令牌 |

### 置信度级别

- `HIGH`：源码中有明确的检查，直接说明了该规则，推断无歧义。
- `SPECULATIVE`：规则从模式、命名约定或部分证据推断。需清楚标注。

```python
# HIGH 置信度：找到了明确的检查
# 来源：UserService.java:89 — `if (!currentUser.getId().equals(resource.getOwnerId())) throw new ForbiddenException()`
assert resp.json()["code"] != 1  # L5[HIGH]：非所有者不能修改

# SPECULATIVE：仅从命名模式推断
# 来源：DataMapService.java — 查询前调用了名为 "checkDataMapAccess" 的方法，但未阅读方法体
assert resp.json()["code"] != 1  # L5[SPECULATIVE]：根据方法名推断可能存在访问检查
```

**不要在 `interface/` 测试中生成 SPECULATIVE 断言** — 接口测试只允许 HIGH 置信度断言。`scenariotest/` 中允许所有置信度级别。

---

## 汇总：各层需生成的内容

| 层级 | 输入                                                    | 输出                                                     |
| ---- | ------------------------------------------------------- | -------------------------------------------------------- |
| L1   | HAR `response.status`、`time_ms`、`Content-Type` 请求头 | `assert_protocol(response, ...)` 调用                    |
| L2   | HAR 响应体 JSON + 源码 DTO/VO                           | Pydantic `BaseModel` + `model_validate(response.json())` |
| L3   | 源码枚举、`@Min`/`@Max`、字段名、分页                   | `assert value in (...)`、范围检查、格式正则              |
| L4   | 源码业务逻辑、状态机、DAO SQL                           | 多步 API 断言，可选 `if db:` DB 检查                     |
| L5   | 深度源码阅读、方法名、注释                              | 含 `来源:行号` + 置信度注释的断言                        |

---

## 补充规则

### L1 响应时间处理

- 当 HAR `response.time_ms` 为 0（连接已建立但无响应计时）时，使用 `max_time_ms = 1000` 作为默认上限
- `max_time_ms` 的计算公式：`max(har_time_ms × 3, 1000)`
- 生成的断言应使用 `assert_protocol()` 而非手动比较

### L3 枚举缺失处理

- 当 HAR 响应中的枚举值不在源码定义的枚举范围内时：
  - 若置信度 HIGH：标记为「可能的未文档化枚举值」，生成 `assert value in known_values` 但添加注释
  - 若置信度 LOW：跳过该枚举断言，在 review-report 中标记为待确认

### 认证逻辑复用

- 当 `tide-config.yaml` 指定 `auth_method: reuse` 时：
  - 优先查找项目中已有的 `conftest.py` 认证 fixture
  - 若未找到，生成标准 `@pytest.fixture` 认证逻辑并输出警告
  - 绝不硬编码 token 或密码
