# Python 测试代码风格指南

> 引用方：`agents/case-writer.md`
> 用途：`case-writer` Agent 的代码生成规则。每个生成的测试文件都必须遵守这些规则。

---

## 已有项目风格优先规则

当 `autoflow-config.yaml` 中 `project.type` 为 `existing` 时：

1. **目录结构**：使用项目已有的测试入口目录（如 `testcases/`），不创建 `tests/`
2. **API 封装**：遵循项目已有的 API 定义模式（如 Enum 类、常量等）
3. **Request 封装**：继承项目已有的请求基类（如 `BaseRequests`），不使用 httpx
4. **断言风格**：使用项目已有的断言模式（如 `resp['code'] == 1`）
5. **认证方式**：复用项目已有的认证逻辑（如 `BaseCookies`）
6. **Allure 使用**：遵循项目已有的 allure 装饰器层级

**以上规则优先于本文档中的默认规范。** 当已有项目风格与 AutoFlow 默认风格冲突时，以已有项目风格为准。

---

## 1. 文件结构

每个生成的测试文件按以下从上到下的顺序组织——不得例外：

```python
"""模块文档字符串：说明此文件测试的内容。

测试目标：POST /dassets/v1/datamap/recentQuery
源码：dt-center-assets / DataMapController.java
"""
# 1. 标准库导入
import re
from dataclasses import dataclass

# 2. 第三方库导入（组内按字母顺序）
import allure
import pytest
from pydantic import BaseModel

# 3. 内部导入
from core.assertions import assert_protocol
from core.client import APIClient

# 4. 常量（模块级，UPPER_SNAKE_CASE 命名）
VALID_META_TYPES = {1, 4, 5, 6, 7, 10}  # 来自 MetaTypeEnum
BUSINESS_SUCCESS_CODE = 1

# 5. Pydantic 响应模型（在测试类之前定义）
class DataItem(BaseModel):
    type: int
    count: int

class AssetStatisticsResponse(BaseModel):
    code: int
    message: str | None = None
    data: list[DataItem]
    success: bool

# 6. 带 allure 装饰器的测试类
@allure.epic("dassets")
@allure.feature("datamap")
class TestDatamapAssetStatistics:
    ...
```

---

## 2. 命名约定

### 2.1 文件名

```
test_{module}.py
```

示例：
- `test_datamap.py` — `/dassets/v1/datamap/` 接口的测试
- `test_sync_task.py` — `/dmetadata/v1/syncTask/` 接口的测试
- `test_sync_task_crud.py` — syncTask 的 CRUD 闭环测试

### 2.2 类名

```
Test{Module}{Feature}
```

示例：
- `TestDatamapRecentQuery` — `recentQuery` 接口的测试
- `TestDatamapAssetStatistics` — `assetStatistics` 接口的测试
- `TestSyncTaskCRUD` — syncTask 的 CRUD 生命周期测试

### 2.3 方法名

```
test_{feature}_{scenario}
```

示例：
- `test_recent_query_with_recorded_params` — HAR 直接场景
- `test_recent_query_missing_required_field` — 参数校验场景
- `test_asset_statistics_returns_valid_types` — L3 枚举校验场景
- `test_sync_task_crud_lifecycle` — CRUD 闭环场景

### 2.4 模型名

```
{EndpointName}Response       # 顶层响应模型
{FieldName}Item              # 列表中的单项
{FieldName}Page              # 分页包装模型
```

示例：
- `AssetStatisticsResponse`、`AssetStatisticsItem`
- `PageTaskResponse`、`PageData`、`TaskItem`

---

## 3. Allure 装饰器层级

在每个测试类和方法上按以下顺序应用 allure 装饰器：

```python
@allure.epic("service_name")          # 如 "dassets"、"dmetadata"
@allure.feature("module_name")        # 如 "datamap"、"syncTask"
class TestModuleFeature:

    @allure.story("scenario_category")  # 如 "har_direct"、"crud_closure"
    @allure.title("人类可读的测试标题")
    @allure.severity(allure.severity_level.CRITICAL)  # BLOCKER/CRITICAL/NORMAL/MINOR/TRIVIAL
    def test_feature_scenario(self, client: APIClient) -> None:
        ...
```

**严重程度映射**：
| 场景类别 | 严重程度 |
|---------|---------|
| CRUD 闭环 | `CRITICAL` |
| HAR 直接场景（正常路径） | `CRITICAL` |
| 权限校验 | `CRITICAL` |
| 参数校验 | `NORMAL` |
| 边界值 | `NORMAL` |
| 状态转换 | `CRITICAL` |
| 关联数据联动 | `CRITICAL` |
| 异常路径 | `NORMAL` |

---

## 4. 断言顺序

在每个测试方法中，断言顺序必须为：L1 → L2 → L3 → L4 → L5。

```python
def test_asset_statistics_success(self, client: APIClient) -> None:
    # 准备（Arrange）
    payload = {"type": 1}

    # 执行（Act）
    resp = client.post("/dassets/v1/datamap/assetStatistics", json=payload)

    # L1 — 协议层
    assert_protocol(resp, expected_status=200, max_time_ms=360)

    # L2 — 结构层
    body = AssetStatisticsResponse.model_validate(resp.json())

    # L3 — 数据层
    assert body.code == BUSINESS_SUCCESS_CODE
    for item in body.data:
        assert item.type in VALID_META_TYPES, f"无效的 meta 类型：{item.type}"
        assert item.count >= 0

    # L4 — 业务层（仅在 scenariotest 中或明确规划时使用）
    # （接口测试中除非特别需要，否则省略）

    # L5 — AI 推断层（仅在规划了 L5 断言时使用，需附必要注释）
    # （除非此场景有规划的 L5 断言，否则省略）
```

**不要混用断言层** — 所有 L1 断言完成后再写 L2，所有 L2 完成后再写 L3，以此类推。

---

## 5. L2 — Pydantic 模型用法

L2 结构断言必须使用 `model_validate()`——绝不手动检查字段是否存在。

```python
# 正确：model_validate 在结构错误时抛出 ValidationError
body = AssetStatisticsResponse.model_validate(resp.json())

# 错误：手动字段检查既脆弱又冗长
data = resp.json()
assert "code" in data
assert "data" in data
assert isinstance(data["data"], list)
```

**Pydantic 模型放置位置**：在测试类上方定义为模块级类，绝不在测试方法内部定义。

**可选字段**：使用 `field: Type | None = None` 表示可能不存在的字段，不得使用 `Optional[Type]`——请使用联合类型语法。

---

## 6. L5 — AI 推断断言要求

每个 L5 断言块上方必须有如下格式的注释：
1. `L5[置信度]:` 标签
2. 相对于 `.repos/` 的源文件路径
3. 行号
4. 一句话说明推断依据

```python
# L5[HIGH]: DataTableService.java:234 — previewData() 调用了 judgeOpenDataPreviewByParam()，
# 该方法会拒绝不存在或未授权的表的请求。
assert resp.json()["code"] != BUSINESS_SUCCESS_CODE, (
    "不存在的 tableId 应被权限检查拒绝"
)
```

没有此注释则绝不生成 L5 断言。若无法确定源码位置，将置信度设为 `SPECULATIVE` 并注明限制。

---

## 7. 数据管理 — API Fixture

通过 API 创建的测试数据使用带 `yield` 的 pytest fixture 管理。绝不直接写入数据库。

### 7.1 模块级 fixture（用于开销较大的初始化）

```python
@pytest.fixture(scope="module")
def created_task_id(client: APIClient) -> Generator[int, None, None]:
    """为整个模块创建同步任务，所有测试完成后清理。"""
    resp = client.post("/dmetadata/v1/syncTask/add", json={
        "taskName": "autoflow_test_task",
        "datasourceId": 1,
    })
    task_id = resp.json()["data"]
    yield task_id
    # 清理 — 即使测试失败也会执行
    client.post("/dmetadata/v1/syncTask/delete", json={"id": task_id})
```

### 7.2 函数级 fixture（用于隔离测试）

```python
@pytest.fixture
def fresh_task(client: APIClient) -> Generator[dict, None, None]:
    """为每个测试创建新任务，测试完成后删除。"""
    resp = client.post("/dmetadata/v1/syncTask/add", json={
        "taskName": f"autoflow_test_{id(object())}",  # 唯一名称
    })
    task = resp.json()["data"]
    yield task
    client.post("/dmetadata/v1/syncTask/delete", json={"id": task["id"]})
```

### 7.3 Fixture 数据规则

- 所有测试创建的数据名称使用 `autoflow_test_` 前缀——便于清理
- 只读 fixture 使用 `scope="module"`（查询已存在数据）
- 写 fixture 使用 `scope="function"`（每个测试创建并修改）
- 绝不在测试间共享可变 fixture 状态
- 必须清理：使用 `yield` + 清理代码，或 `pytest.fixture(autouse=True)` 清理

---

## 8. 不可变性规则

**值对象使用冻结数据类（frozen dataclass）** — 绝不为测试数据创建可变类。

```python
# 正确：frozen=True 防止修改
@dataclass(frozen=True)
class QueryParams:
    current_page: int = 1
    page_size: int = 10
    keyword: str = ""

# 错误：可变类可能被意外修改
class QueryParams:
    def __init__(self):
        self.current_page = 1
```

**绝不修改 fixture 对象**：

```python
# 错误：修改了 fixture
def test_update_task(self, created_task: dict) -> None:
    created_task["name"] = "new_name"  # 修改行为！

# 正确：创建新字典
def test_update_task(self, created_task: dict) -> None:
    update_payload = {**created_task, "taskName": "new_name"}  # 新对象
```

---

## 9. 规模限制

| 单元 | 限制 | 超出时的处理方式 |
|------|------|---------------|
| 文件 | 400 行 | 按接口组或场景类别拆分 |
| 测试方法 | 50 行 | 将步骤提取为辅助方法或 fixture |
| Fixture | 30 行 | 将初始化逻辑提取为辅助函数 |
| 嵌套深度 | 4 层 | 用提前返回或辅助方法展平 |

**文件超过 400 行时的拆分方式**：

```
# 拆分前（过大）：
tests/interface/dassets_datamap/test_datamap.py   # 650 行

# 拆分后（按接口拆分）：
tests/interface/dassets_datamap/test_datamap_query.py    # recent_query + asset_statistics
tests/interface/dassets_datamap/test_datamap_manage.py   # add + update + delete
```

---

## 10. 禁止模式

以下模式在生成的测试代码中**绝对不允许**使用：

### 10.1 禁止硬编码值

```python
# 错误：硬编码
assert body.data[0].type == 1

# 正确：使用命名常量
ASSET_TYPE_TABLE = 1
assert body.data[0].type == ASSET_TYPE_TABLE
```

例外：用于"不存在"场景的测试专用 ID（如 `999999999`）允许使用，但需加注释。

### 10.2 禁止 print 语句

```python
# 错误
print(f"响应：{resp.json()}")

# 正确：使用 allure.attach 记录调试信息
allure.attach(str(resp.json()), name="response_body", attachment_type=allure.attachment_type.JSON)
```

### 10.3 禁止深层嵌套

```python
# 错误：5+ 层嵌套
def test_complex(self, client):
    if condition1:
        for item in items:
            if condition2:
                for sub in item.subs:
                    if condition3:
                        assert sub.value == 1  # 第 5 层

# 正确：用提前返回和辅助方法展平
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

### 10.4 禁止修改共享状态

```python
# 错误：修改了共享 fixture 字典
def test_a(self, shared_data: dict) -> None:
    shared_data["key"] = "new_value"  # 影响其他测试！

# 正确：创建新对象
def test_a(self, shared_data: dict) -> None:
    local_data = {**shared_data, "key": "new_value"}
```

### 10.5 禁止直接写入 DB

```python
# 错误：直接插入测试数据
def test_with_db_data(self, db: DBHelper) -> None:
    db.execute("INSERT INTO sync_task ...")  # DBHelper 没有写入方法

# 正确：通过 API 创建数据
def test_with_api_data(self, client: APIClient) -> None:
    resp = client.post("/dmetadata/v1/syncTask/add", json={...})
    task_id = resp.json()["data"]
```

`DBHelper` 只有只读方法：`query_one`、`query_all`、`count`。

---

## 11. 导入规范

```python
# 标准库 — 不使用别名
from pathlib import Path
from dataclasses import dataclass
from typing import Generator

# 第三方库 — 不使用别名（约定俗成的除外）
import allure
import pytest
from pydantic import BaseModel

# 内部导入 — 显式导入，绝不使用通配符
from core.assertions import assert_protocol
from core.client import APIClient
from core.db import DBHelper
```

绝不使用 `from module import *`。

---

## 12. 类型注解

所有函数签名必须包含类型注解：

```python
# 正确
def test_query_success(self, client: APIClient, db: DBHelper | None) -> None:
    ...

@pytest.fixture
def task_id(self, client: APIClient) -> Generator[int, None, None]:
    ...

# 错误：缺少注解
def test_query_success(self, client, db):
    ...
```

---

## 13. 完成文件前的快速检查清单

- [ ] 文件以模块文档字符串开头
- [ ] 所有导入已按规范组织（标准库 → 第三方 → 内部）
- [ ] 所有常量已在模块级用命名方式定义
- [ ] 所有 Pydantic 模型已在测试类之前定义
- [ ] 每个测试类都有 `@allure.epic`、`@allure.feature` 装饰器
- [ ] 每个测试方法都有 `@allure.story`、`@allure.title`、`@allure.severity`
- [ ] 断言顺序为 L1 → L2 → L3 → L4 → L5
- [ ] L2 仅使用 `model_validate()`
- [ ] L5 断言有 `L5[置信度]: 来源:行号 推断依据` 注释
- [ ] 所有 fixture 使用 `yield` 加清理代码
- [ ] 没有 `print()` 语句
- [ ] 没有硬编码值（有文档说明的异常 ID 除外）
- [ ] 没有修改共享对象
- [ ] 文件不超过 400 行
- [ ] 所有测试方法不超过 50 行
- [ ] 所有函数有类型注解
