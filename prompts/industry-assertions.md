# 行业特定断言规范

> 引用方：`agents/case-writer.md`、`agents/scenario-analyzer.md`、`agents/case-reviewer.md`
> 用途：根据 `tide-config.yaml` 中的 `industry.domain` 字段，为测试生成添加行业特定的断言和场景。

---

## 使用方式

1. 读取 `tide-config.yaml` 中的 `industry.domain` 字段
2. 若字段存在，查找下方对应行业的断言规则
3. 在正常 L1-L5 断言之后，追加行业特定断言
4. 行业断言统一标注为 `# Industry[<行业>]: <断言说明>`

---

## 金融 / 银行 / 保险

### 必须追加的场景类别

| 场景类型       | 触发条件                       | 说明                                   |
| -------------- | ------------------------------ | -------------------------------------- |
| `idempotency`  | POST/PUT 写入类接口            | 相同请求发两次，第二次应返回幂等响应   |
| `audit_log`    | 所有写入类接口                 | 操作完成后审计日志表应有对应记录       |
| `data_masking` | 响应包含手机号/身份证/银行卡号 | 敏感字段应脱敏展示（如 `138****1234`） |

### 断言示例

```python
# Industry[金融]: 幂等性检查 — 重复提交相同交易应被拒绝或返回相同结果
resp1 = client.post(endpoint, json=payload)
resp2 = client.post(endpoint, json=payload)
assert resp2.status_code in (200, 409), "重复请求应返回成功(幂等)或冲突"

# Industry[金融]: 敏感数据脱敏 — 手机号应部分隐藏
import re
phone = body.data.phone
if phone:
    assert re.match(r"\d{3}\*{4}\d{4}", phone), f"手机号未脱敏: {phone}"

# Industry[金融]: 审计日志 — 写入操作应产生审计记录
if db:
    audit = db.query_one(
        "SELECT * FROM audit_log WHERE operation_id = %s ORDER BY created_at DESC",
        (operation_id,),
    )
    assert audit is not None, "缺少审计日志记录"
```

---

## 医疗 / 健康

### 必须追加的场景类别

| 场景类型         | 触发条件                     | 说明                         |
| ---------------- | ---------------------------- | ---------------------------- |
| `phi_masking`    | 响应包含患者姓名/诊断/病历号 | PHI 字段应脱敏或按权限控制   |
| `access_control` | 所有患者数据接口             | 不同角色看到不同范围的数据   |
| `consent_check`  | 数据共享/导出接口            | 操作前应检查患者知情同意状态 |

### 断言示例

```python
# Industry[医疗]: PHI 字段脱敏 — 患者姓名应部分隐藏
patient_name = body.data.patient_name
if patient_name and len(patient_name) > 1:
    assert "*" in patient_name, f"患者姓名未脱敏: {patient_name}"

# Industry[医疗]: 越权访问 — 其他科室医生不应看到本科室患者
resp = client.get(endpoint, headers=other_dept_headers)
assert resp.status_code == 403, "跨科室访问应被拒绝"
```

---

## 电商 / 零售

### 必须追加的场景类别

| 场景类型                | 触发条件           | 说明                           |
| ----------------------- | ------------------ | ------------------------------ |
| `inventory_consistency` | 下单/退货接口      | 操作前后库存数量应一致变化     |
| `price_precision`       | 涉及金额计算的接口 | 金额应精确到分，无浮点精度问题 |
| `concurrent_order`      | 下单接口           | 并发下单不应超卖               |

### 断言示例

```python
# Industry[电商]: 价格精度 — 金额字段应为精确值（非浮点）
from decimal import Decimal
price = Decimal(str(body.data.total_amount))
assert price == price.quantize(Decimal("0.01")), f"金额精度异常: {price}"

# Industry[电商]: 库存一致性 — 下单后库存应减少
stock_before = client.get(f"/api/v1/products/{product_id}").json()["data"]["stock"]
client.post("/api/v1/orders", json=order_payload)
stock_after = client.get(f"/api/v1/products/{product_id}").json()["data"]["stock"]
assert stock_after == stock_before - order_quantity, "库存变化不一致"
```

---

## 互联网 / SaaS

### 必须追加的场景类别

| 场景类型           | 触发条件             | 说明                            |
| ------------------ | -------------------- | ------------------------------- |
| `tenant_isolation` | 多租户系统的数据接口 | 租户 A 不应看到租户 B 的数据    |
| `rate_limit`       | 公开 API 接口        | 超过限流阈值应返回 429          |
| `version_compat`   | 多版本 API 共存      | v1 和 v2 接口应各自返回正确格式 |

### 断言示例

```python
# Industry[SaaS]: 多租户隔离 — 租户 A 不应访问到租户 B 的资源
resp = client.get(f"/api/v1/resources/{tenant_b_resource_id}", headers=tenant_a_headers)
assert resp.status_code in (403, 404), "租户隔离失败"

# Industry[SaaS]: 限流 — 超过阈值应返回 429
for _ in range(RATE_LIMIT + 1):
    resp = client.get(endpoint)
last_resp = resp
assert last_resp.status_code == 429, "未触发限流"
```

---

## 通用（未匹配行业时使用）

不追加任何行业特定断言。仅使用标准 L1-L5 断言。

---

## 行业断言在审查中的检查

`case-reviewer` 在审查时应额外检查：

1. 若 `tide-config.yaml` 中有 `industry.domain`，检查生成的测试是否包含对应行业的必须场景
2. 缺少行业必须场景的文件，标记为 `MEDIUM` 严重程度
3. 行业断言不准确的（如金融行业的幂等性检查逻辑错误），标记为 `HIGH`
