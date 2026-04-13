# 生成项目最佳实践

## conftest.py 推荐结构

```python
import pytest
from core.client import APIClient

@pytest.fixture(scope="session")
def api_client() -> APIClient:
    """会话级别的 API 客户端 — 所有测试共享同一连接。"""
    return APIClient(base_url="http://localhost:8080")

@pytest.fixture(scope="function")
def db(api_client: APIClient):
    """函数级别的数据库连接 — 每个测试独立事务。"""
    from core.db import DBHelper
    helper = DBHelper(...)
    yield helper
    helper.close()
```

## fixture 设计模式

| 模式 | scope | 适用场景 |
|------|-------|---------|
| API 客户端 | session | 所有测试共享，避免重复创建连接 |
| 数据库连接 | function | 每个测试独立事务，防止数据污染 |
| 测试数据工厂 | function | 动态生成测试数据，测试间隔离 |
| 认证 token | session | 登录一次，全局复用 |

## 目录结构约定

```
tests/
├── interface/        # 接口测试（L1-L3 断言）
│   └── test_xxx.py   # 按服务/模块组织
├── scenariotest/     # 场景测试（L1-L5 断言）
│   └── test_xxx.py   # 按业务流程组织
├── unittest/         # 单元测试（L3-L5 断言）
│   └── test_xxx.py   # 按工具类组织
└── conftest.py       # 全局 fixture
```

## Allure 标签约定

```python
import allure

@allure.epic("数据资产")
@allure.feature("数据地图")
@allure.story("最近查询")
class TestRecentQuery:
    @allure.severity(allure.severity_level.CRITICAL)
    def test_query_success(self, api_client):
        ...
```
