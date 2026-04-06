# 断言示例参考（L1-L5）

本文档收录各类常见 API 场景的 L1-L5 断言代码示例，供 `case-writer` Agent 生成测试时参考。  
文档不加载到 Agent 上下文，仅供人工查阅。

---

## 目录

- [列表查询（List）](#列表查询)
- [详情查询（Detail）](#详情查询)
- [创建（Create）](#创建)
- [更新（Update）](#更新)
- [删除（Delete）](#删除)
- [分页（Pagination）](#分页)
- [权限拒绝（Permission Denied）](#权限拒绝)
- [参数校验（Validation Error）](#参数校验)

---

## 列表查询

场景：`GET /api/v1/users` 返回用户列表。

```python
import pytest
import httpx
from pydantic import BaseModel, field_validator
from typing import List, Optional
import time


class UserItem(BaseModel):
    id: int
    username: str
    email: str
    status: str
    created_at: str

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        allowed = {"active", "inactive", "banned"}
        assert v in allowed, f"status {v!r} not in {allowed}"
        return v


class UserListResponse(BaseModel):
    code: int
    data: List[UserItem]
    total: int
    page: int
    page_size: int


def test_user_list(client: httpx.Client, auth_headers: dict) -> None:
    # ── L1 协议层 ──────────────────────────────────────────────────
    start = time.time()
    resp = client.get("/api/v1/users", headers=auth_headers)
    elapsed_ms = (time.time() - start) * 1000

    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}"
    assert elapsed_ms < 2000, f"响应时间 {elapsed_ms:.0f}ms 超过 2000ms 阈值"
    assert "application/json" in resp.headers["content-type"]

    # ── L2 结构层 ──────────────────────────────────────────────────
    body = UserListResponse.model_validate(resp.json())

    # ── L3 数据层 ──────────────────────────────────────────────────
    assert body.code == 0, f"业务码期望 0，实际 {body.code}"
    assert body.total >= 0
    assert 1 <= body.page_size <= 100, "page_size 应在 1-100 之间"
    for item in body.data:
        assert "@" in item.email, f"用户 {item.id} 的 email 格式非法"

    # ── L4 业务层 ──────────────────────────────────────────────────
    ids = [item.id for item in body.data]
    assert len(ids) == len(set(ids)), "列表中存在重复 id"
    assert len(body.data) <= body.page_size, "返回条数不应超过 page_size"

    # ── L5 AI 推断层 ───────────────────────────────────────────────
    # 隐式规则：已封禁用户（banned）不应出现在默认列表中
    banned_items = [item for item in body.data if item.status == "banned"]
    assert len(banned_items) == 0, (
        f"发现 {len(banned_items)} 个 banned 用户出现在默认列表中，"
        "疑似缺少过滤逻辑"
    )
```

---

## 详情查询

场景：`GET /api/v1/users/{id}` 返回单个用户。

```python
class UserDetail(BaseModel):
    id: int
    username: str
    email: str
    status: str
    roles: List[str]
    created_at: str
    updated_at: str


class UserDetailResponse(BaseModel):
    code: int
    data: UserDetail


def test_user_detail(client: httpx.Client, auth_headers: dict, existing_user_id: int) -> None:
    # ── L1 ────────────────────────────────────────────────────────
    resp = client.get(f"/api/v1/users/{existing_user_id}", headers=auth_headers)
    assert resp.status_code == 200

    # ── L2 ────────────────────────────────────────────────────────
    body = UserDetailResponse.model_validate(resp.json())

    # ── L3 ────────────────────────────────────────────────────────
    assert body.data.id == existing_user_id
    assert len(body.data.username) >= 2, "用户名长度不应小于 2"
    assert body.data.updated_at >= body.data.created_at, "更新时间不能早于创建时间"

    # ── L4 ────────────────────────────────────────────────────────
    # 验证数据库中确实存在该用户（需要 db fixture）
    # db_user = db_session.execute("SELECT id FROM users WHERE id = ?", [existing_user_id]).fetchone()
    # assert db_user is not None, f"数据库中不存在 id={existing_user_id} 的用户"

    # ── L5 ────────────────────────────────────────────────────────
    # 隐式规则：roles 列表至少包含一个角色（业务约定：用户必须有默认角色）
    assert len(body.data.roles) >= 1, "用户至少应有一个角色"


def test_user_detail_not_found(client: httpx.Client, auth_headers: dict) -> None:
    resp = client.get("/api/v1/users/999999999", headers=auth_headers)
    assert resp.status_code == 404
    body = resp.json()
    assert "message" in body or "msg" in body, "404 响应应包含错误描述字段"
```

---

## 创建

场景：`POST /api/v1/users` 创建用户。

```python
import uuid


def test_create_user(client: httpx.Client, auth_headers: dict) -> None:
    unique_suffix = uuid.uuid4().hex[:8]
    payload = {
        "username": f"testuser_{unique_suffix}",
        "email": f"test_{unique_suffix}@example.com",
        "password": "Test@1234567",
        "role_ids": [1],
    }

    # ── L1 ────────────────────────────────────────────────────────
    resp = client.post("/api/v1/users", json=payload, headers=auth_headers)
    assert resp.status_code == 201, f"创建应返回 201，实际 {resp.status_code}: {resp.text}"

    # ── L2 ────────────────────────────────────────────────────────
    body = UserDetailResponse.model_validate(resp.json())

    # ── L3 ────────────────────────────────────────────────────────
    assert body.data.username == payload["username"]
    assert body.data.email == payload["email"]
    assert body.data.status == "active", "新建用户默认状态应为 active"

    # ── L4 ────────────────────────────────────────────────────────
    # 幂等验证：再次创建相同 email 应返回 409
    resp2 = client.post("/api/v1/users", json=payload, headers=auth_headers)
    assert resp2.status_code == 409, "重复 email 应返回 409 Conflict"

    # ── L5 ────────────────────────────────────────────────────────
    # 隐式规则：密码字段不应出现在响应体中
    resp_dict = resp.json()
    assert "password" not in str(resp_dict), "响应体中不应包含 password 字段（安全边界）"


def test_create_user_invalid_email(client: httpx.Client, auth_headers: dict) -> None:
    payload = {"username": "bad_user", "email": "not-an-email", "password": "Test@123"}
    resp = client.post("/api/v1/users", json=payload, headers=auth_headers)
    assert resp.status_code == 422, "非法 email 应返回 422"
```

---

## 更新

场景：`PUT /api/v1/users/{id}` 全量更新用户信息。

```python
def test_update_user(
    client: httpx.Client,
    auth_headers: dict,
    existing_user_id: int,
) -> None:
    update_payload = {
        "username": "updated_username",
        "email": "updated@example.com",
    }

    # ── L1 ────────────────────────────────────────────────────────
    resp = client.put(
        f"/api/v1/users/{existing_user_id}",
        json=update_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # ── L2 ────────────────────────────────────────────────────────
    body = UserDetailResponse.model_validate(resp.json())

    # ── L3 ────────────────────────────────────────────────────────
    assert body.data.username == update_payload["username"]
    assert body.data.email == update_payload["email"]

    # ── L4 ────────────────────────────────────────────────────────
    # CRUD 一致性：GET 验证更新已持久化
    get_resp = client.get(f"/api/v1/users/{existing_user_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    get_body = UserDetailResponse.model_validate(get_resp.json())
    assert get_body.data.username == update_payload["username"]
    assert get_body.data.email == update_payload["email"]

    # ── L5 ────────────────────────────────────────────────────────
    # 隐式规则：updated_at 应比原值更新（状态机时间戳单调递增）
    assert get_body.data.updated_at > body.data.created_at
```

---

## 删除

场景：`DELETE /api/v1/users/{id}` 删除用户（逻辑删除）。

```python
def test_delete_user(
    client: httpx.Client,
    auth_headers: dict,
    created_user_id: int,  # 由 fixture 创建的临时用户
) -> None:
    # ── L1 ────────────────────────────────────────────────────────
    resp = client.delete(f"/api/v1/users/{created_user_id}", headers=auth_headers)
    assert resp.status_code == 204, f"删除应返回 204，实际 {resp.status_code}"

    # ── L2 ────────────────────────────────────────────────────────
    assert resp.content == b"", "204 响应体应为空"

    # ── L4 ────────────────────────────────────────────────────────
    # 验证删除后 GET 返回 404（硬删除）或 status=deleted（软删除）
    get_resp = client.get(f"/api/v1/users/{created_user_id}", headers=auth_headers)
    assert get_resp.status_code in {404, 200}, "删除后 GET 应返回 404 或包含 deleted 状态"
    if get_resp.status_code == 200:
        body = get_resp.json()
        assert body["data"]["status"] == "deleted", "软删除应标记 status=deleted"

    # ── L5 ────────────────────────────────────────────────────────
    # 隐式规则：重复删除应返回 404（幂等性）
    resp2 = client.delete(f"/api/v1/users/{created_user_id}", headers=auth_headers)
    assert resp2.status_code == 404, "重复删除应返回 404（幂等性保证）"
```

---

## 分页

场景：验证分页参数边界行为。

```python
@pytest.mark.parametrize(
    "page, page_size, expect_status",
    [
        (1, 10, 200),    # 正常分页
        (1, 100, 200),   # 最大 page_size
        (0, 10, 422),    # page 从 1 开始
        (1, 0, 422),     # page_size 不能为 0
        (1, 101, 422),   # page_size 超上限
        (99999, 10, 200), # 超出范围的页码返回空列表而非报错
    ],
)
def test_user_list_pagination(
    client: httpx.Client,
    auth_headers: dict,
    page: int,
    page_size: int,
    expect_status: int,
) -> None:
    resp = client.get(
        "/api/v1/users",
        params={"page": page, "page_size": page_size},
        headers=auth_headers,
    )

    # ── L1 ────────────────────────────────────────────────────────
    assert resp.status_code == expect_status

    if expect_status == 200:
        body = resp.json()
        # ── L3 ────────────────────────────────────────────────────
        assert body["page"] == page
        assert body["page_size"] == page_size
        assert isinstance(body["data"], list)
        assert len(body["data"]) <= page_size

        # ── L5 ────────────────────────────────────────────────────
        # 隐式规则：超出范围页码返回空列表，不抛出服务器错误
        if page == 99999:
            assert len(body["data"]) == 0, "超出范围的页码应返回空列表"
```

---

## 权限拒绝

场景：无权限用户访问受保护资源。

```python
def test_list_users_unauthorized(client: httpx.Client) -> None:
    """未携带 Token 应返回 401"""
    resp = client.get("/api/v1/users")

    # ── L1 ────────────────────────────────────────────────────────
    assert resp.status_code == 401

    # ── L2 ────────────────────────────────────────────────────────
    body = resp.json()
    assert "message" in body or "msg" in body

    # ── L5 ────────────────────────────────────────────────────────
    # 安全边界：401 响应不应泄露内部路径、堆栈信息或数据库错误
    resp_text = resp.text
    assert "Traceback" not in resp_text, "401 响应不应包含 Python Traceback"
    assert "SQLException" not in resp_text, "401 响应不应包含数据库异常信息"


def test_delete_user_forbidden(
    client: httpx.Client,
    normal_user_headers: dict,  # 普通用户 token（非管理员）
    existing_user_id: int,
) -> None:
    """普通用户不应能删除其他用户"""
    resp = client.delete(f"/api/v1/users/{existing_user_id}", headers=normal_user_headers)

    # ── L1 ────────────────────────────────────────────────────────
    assert resp.status_code == 403

    # ── L5 ────────────────────────────────────────────────────────
    # 安全边界：403 响应不应泄露目标资源的详细信息
    body = resp.json()
    assert "password" not in str(body)
    assert "hash" not in str(body).lower()
```

---

## 参数校验

场景：必填字段缺失、类型错误、超长字符串等。

```python
@pytest.mark.parametrize(
    "payload, expected_status, desc",
    [
        # 缺少必填字段
        ({"email": "a@b.com"}, 422, "缺少 username"),
        ({"username": "foo"}, 422, "缺少 email"),
        ({}, 422, "全空请求体"),
        # 类型错误
        ({"username": 123, "email": "a@b.com"}, 422, "username 非字符串"),
        # 长度超限（假设 username 最长 50 字符）
        ({"username": "x" * 51, "email": "a@b.com", "password": "Test@123"}, 422, "username 超长"),
        # XSS 注入（L5 安全边界）
        (
            {"username": "<script>alert(1)</script>", "email": "a@b.com", "password": "Test@123"},
            422,
            "XSS 注入应被拒绝",
        ),
        # SQL 注入（L5 安全边界）
        (
            {"username": "' OR 1=1 --", "email": "a@b.com", "password": "Test@123"},
            422,
            "SQL 注入应被拒绝",
        ),
    ],
)
def test_create_user_validation(
    client: httpx.Client,
    auth_headers: dict,
    payload: dict,
    expected_status: int,
    desc: str,
) -> None:
    resp = client.post("/api/v1/users", json=payload, headers=auth_headers)
    assert resp.status_code == expected_status, f"场景「{desc}」期望 {expected_status}，实际 {resp.status_code}"

    if expected_status == 422:
        body = resp.json()
        # ── L2 ────────────────────────────────────────────────────
        assert "detail" in body or "errors" in body or "message" in body, (
            f"422 响应应包含错误详情，场景：{desc}"
        )
```

---

## 说明

- **L4 数据库验证** 依赖 `db_session` fixture（在 `conftest.py` 中配置）
- **L5 AI 推断** 断言来源于 `scenario-analyzer` Agent 对源码的静态分析，由人工在代码评审时确认
- 所有测试建议使用独立数据隔离（每个测试创建自己的数据，teardown 时清理），避免测试间依赖
