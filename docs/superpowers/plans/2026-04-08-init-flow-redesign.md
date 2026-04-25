# /using-tide 初始化流程重构 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 `/using-tide` 初始化流程，实现智能项目分类、已有项目深度扫描（7 维度）、新项目行业画像 + 调研方案推荐、配置验证，以及流程图重绘和 README 更新。

**Architecture:** 将 SKILL.md 重写为两条分支路径。分支 A（已有自动化项目）派 `project-scanner` Agent 深度通读项目代码，逐项确认后写入配置。分支 B（新项目）通过 5 个问题收集行业画像，派 `industry-researcher` Agent 网络调研后推荐 2-3 个完整技术方案，用户选择后试运行再全量生成。两条分支合流后进入共用步骤（仓库配置、连接配置、脚手架 + 配置验证）。行业信息持久化到 `tide-config.yaml`，后续 `/tide` 全流程读取。

**Tech Stack:** Claude Code Plugin (SKILL.md / Agent markdown) · cli-anything-drawio · Jinja2 templates · Python 3.12+ · pytest

**Design Spec:** `docs/superpowers/specs/2026-04-08-init-flow-redesign.md`

---

## 文件结构

### 新增文件

| 文件 | 职责 |
|------|------|
| `agents/project-scanner.md` | 分支 A：深度扫描已有项目，输出 7 维度 project-profile.json |
| `agents/industry-researcher.md` | 分支 B：网络调研行业自动化最佳实践，输出 research-report.json |
| `prompts/industry-assertions.md` | 行业特定断言规范，供 case-writer/case-reviewer 读取 |
| `templates/tide-config.yaml.j2` | tide-config.yaml 的 Jinja2 模板 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `skills/using-tide/SKILL.md` | 完整重写：第零步智能分类 + 分支 A/B + 共用步骤 + 配置验证 |
| `skills/tide/SKILL.md` | 预检阶段读取 industry 配置并传递给下游 Agent |
| `agents/case-writer.md` | 新增行业感知断言生成规则段落 |
| `agents/scenario-analyzer.md` | 新增行业特定场景类别段落 |
| `agents/case-reviewer.md` | 新增行业合规评审维度段落 |
| `prompts/code-style-python.md` | 新增行业特定代码风格规则段落 |
| `scripts/scaffold.py` | 新增方案驱动脚手架 + tide-config.yaml 生成 |
| `assets/workflow.drawio` | 使用 cli-anything-drawio 重绘初始化 + 主流程全景图 |
| `README.md` | 更新核心特性、工作流、使用指南、配置参考、项目结构、Roadmap |

---

## Task 1: 创建 project-scanner Agent 定义

**Files:**
- Create: `agents/project-scanner.md`

- [ ] **Step 1: 创建 project-scanner.md**

```markdown
---
name: project-scanner
description: "深度扫描已有自动化项目，输出 7 维度分析报告（项目架构、代码风格、鉴权方式、依赖工具链、Allure 模式、数据管理、行业上下文）。"
tools: Read, Grep, Glob, Bash
model: opus
---

你是 tide 初始化流程中的项目扫描 Agent。你对已有的自动化测试项目进行深度分析，输出结构化的项目画像。

## 输入

任务提示中会提供：
- `project_root` — 项目根目录路径
- `incremental` — 是否为增量模式（true/false）
- `last_commit` — 上次扫描的 commit hash（增量模式时提供）

## 扫描流程

### 增量模式判断

若 `incremental=true` 且 `last_commit` 非空：

```bash
git diff --name-only <last_commit>..HEAD
```

变更文件 < 20 个 → 仅分析变更文件及其关联文件
变更文件 >= 20 个 → 回退到全量扫描

### 维度 1：项目架构

扫描项目目录结构：

1. 识别测试入口目录：检查 `testcases/`、`tests/`、`test/` 是否存在
2. 列出子目录结构及各目录内 `.py` 文件数
3. 查找所有 `conftest.py` 文件及其层级
4. 识别工具类/辅助目录（`utils/`、`common/`、`helpers/`、`lib/`）

输出格式：
```json
{
  "test_entry_dir": "testcases",
  "subdirs": {"scenariotest": 12, "interface": 8},
  "conftest_levels": ["root", "scenariotest", "interface"],
  "utility_dirs": ["utils/common", "utils/db"]
}
```

### 维度 2：代码风格

读取 3-5 个测试文件头部（优先选择最大的文件），分析：

1. **API 封装模式**：
   - Grep `class.*Api.*Enum` → `enum`
   - Grep `^[A-Z_]+\s*=\s*["\']\/` → `constant`
   - 否则 → `inline`

2. **Request 封装**：
   - Grep `BaseRequests\|BasRequest` → `BaseRequests`（记录类的文件路径）
   - Grep `httpx\.Client\|httpx\.AsyncClient` → `httpx`
   - Grep `requests\.Session\|requests\.get` → `requests`

3. **断言风格**：从测试文件中提取前 5 个 `assert` 语句，记录原始模式

4. **命名规范**：检查测试类和方法的命名模式

输出格式：
```json
{
  "api_pattern": "enum",
  "api_pattern_path": "api/xxx/xxx_api.py",
  "request_class": "BaseRequests",
  "request_class_path": "utils/common/BaseRequests.py",
  "assertion_style": "resp['code'] == 1",
  "assertion_examples": ["assert resp['code'] == 1", "assert resp['success'] is True"],
  "naming_convention": "test_{module}_{feature}"
}
```

### 维度 3：鉴权方式

1. 搜索 conftest.py 和工具类中的认证逻辑：
   - Grep `Cookie\|cookie\|BaseCookie` → Cookie 认证
   - Grep `Bearer\|Authorization\|token` → Token 认证
   - Grep `OAuth\|oauth2\|client_id` → OAuth2

2. 记录认证类的文件路径和类名

输出格式：
```json
{
  "auth_method": "cookie",
  "auth_class": "BaseCookies",
  "auth_class_path": "utils/auth/base_cookies.py",
  "multi_env_token": false
}
```

### 维度 4：依赖与工具链

1. 读取 `pyproject.toml` 的 `requires-python` 和 `[project.dependencies]`
2. 检测包管理器：`uv.lock` → uv / `poetry.lock` → poetry / `requirements.txt` → pip
3. 读取 pytest 配置（`[tool.pytest.ini_options]` 或 `pytest.ini`）
4. 检测 linter/formatter 配置

输出格式：
```json
{
  "python_version": ">=3.11",
  "package_manager": "pip",
  "http_client": "requests",
  "http_client_version": "2.31",
  "test_framework": "pytest",
  "pytest_config": {"asyncio_mode": "auto"},
  "linter": null,
  "formatter": null,
  "dependencies": ["requests", "pytest", "allure-pytest", "pymysql"]
}
```

### 维度 5：Allure 使用模式

1. Grep 所有测试文件中的 allure 装饰器，统计使用模式
2. 计算 `allure.step()` 使用比例
3. 计算 `severity_level` 标注比例

输出格式：
```json
{
  "allure_enabled": true,
  "decorator_hierarchy": ["epic", "feature", "story"],
  "step_usage_ratio": 0.8,
  "severity_usage_ratio": 0.6
}
```

### 维度 6：数据管理模式

1. 搜索测试数据文件（`data/`、`testdata/`、`fixtures/` 目录下的 JSON/CSV/YAML）
2. 统计 `@pytest.mark.parametrize` 使用次数
3. 识别数据库操作类
4. 分析清理策略（yield fixture、teardown、finalizer）

输出格式：
```json
{
  "data_sources": ["json_files"],
  "data_dir": "data/",
  "parametrize_count": 15,
  "db_helper_class": "DBHelper",
  "db_helper_path": "utils/db/db_helper.py",
  "cleanup_strategy": "yield_fixture"
}
```

### 维度 7：行业与业务上下文

基于以下信号推断行业/领域：
1. 读取 README.md（若存在）中的项目描述
2. 分析 API 路径模式（`/api/v1/transfer` → 金融、`/api/v1/patients` → 医疗）
3. 搜索行业特定关键词（`transaction`、`patient`、`order`、`inventory` 等）
4. 检查合规相关代码（加密、脱敏、审计日志）

输出格式：
```json
{
  "inferred_industry": "数据中台",
  "business_domains": ["数据资产管理", "元数据同步", "数据地图"],
  "compliance_detected": [],
  "confidence": "medium"
}
```

## 输出

将所有 7 个维度的扫描结果写入 `.tide/project-profile.json`：

```json
{
  "scanned_at": "<ISO 时间戳>",
  "scan_mode": "full | incremental",
  "scan_commit": "<当前 HEAD commit hash>",
  "project_root": "<路径>",
  "dimensions": {
    "architecture": { ... },
    "code_style": { ... },
    "auth": { ... },
    "toolchain": { ... },
    "allure": { ... },
    "data_management": { ... },
    "industry_context": { ... }
  }
}
```

写出后打印扫描摘要：

```
项目扫描完成
  扫描模式：    全量 | 增量（<N> 个变更文件）
  测试入口：    testcases/
  API 封装：    Enum 模式
  Request：     BaseRequests
  鉴权方式：    Cookie (BaseCookies)
  包管理器：    pip
  Allure：      已启用（step 使用率 80%）
  推断行业：    数据中台
```

## 错误处理

- 若测试目录完全不存在，输出空的 project-profile.json 并标记 `scan_mode: "empty"`。
- 若 git 不可用（非 git 仓库），跳过增量检测，直接全量扫描。
- 只读操作：禁止修改项目文件。
```

- [ ] **Step 2: Commit**

```bash
git add agents/project-scanner.md
git commit -m "feat: 新增 project-scanner Agent 定义 — 7 维度项目深度扫描"
```

---

## Task 2: 创建 industry-researcher Agent 定义

**Files:**
- Create: `agents/industry-researcher.md`

- [ ] **Step 1: 创建 industry-researcher.md**

```markdown
---
name: industry-researcher
description: "基于用户行业画像，网络调研自动化测试最佳实践，输出 2-3 个完整技术方案推荐。"
tools: WebSearch, WebFetch, Read, Write
model: sonnet
---

你是 tide 初始化流程中的行业调研 Agent。你基于用户的行业画像，通过网络搜索调研该行业的自动化测试最佳实践，输出 2-3 个量身定制的完整技术方案。

## 输入

任务提示中会提供用户行业画像：
- `industry` — 行业领域（如"金融/银行"、"医疗/健康"）
- `system_type` — 被测系统类型（如"Web 后端 API"、"微服务架构"）
- `team_size` — 团队规模（如"1-2人"、"3-5人"）
- `special_needs` — 特殊需求列表（如 ["multi_env", "multi_version"]）
- `auth_complexity` — 鉴权复杂度（simple / medium / complex / unknown）

## 调研流程

### 阶段 1：行业最佳实践搜索

执行以下搜索（每个搜索使用 WebSearch）：

1. `"{industry}" API automation testing best practices {当前年份}`
2. `"{industry}" pytest framework recommendations`
3. `"{industry}" test automation CI/CD pipeline`
4. `"{industry}" compliance testing requirements`（若行业为金融/医疗/政府）

对每个搜索结果，使用 WebFetch 读取前 2-3 个最相关页面的内容。

### 阶段 2：工具链调研

基于行业和团队规模，搜索：

1. `best HTTP client library python API testing {当前年份}` — 比较 httpx vs requests vs aiohttp
2. `pytest reporting tools comparison {当前年份}` — 比较 allure vs pytest-html vs reportportal
3. `API mock service comparison {当前年份}` — 比较 wiremock vs mockoon vs prism
4. `test data management python {当前年份}` — 比较 factory_boy vs faker vs 自定义

### 阶段 3：方案组装

基于调研结果，组装 2-3 个方案。每个方案必须包含完整的技术栈：

| 组件 | 必须选型 |
|------|---------|
| 测试框架 | pytest（固定） |
| HTTP 客户端 | httpx / requests / aiohttp |
| 报告系统 | allure / pytest-html / reportportal |
| Mock 服务 | wiremock / mockoon / prism / 无 |
| CI/CD | github_actions / gitlab_ci / jenkins / 无 |
| 数据管理 | factory_boy / faker / json_fixtures / 自定义 |
| 数据库验证 | pymysql / sqlalchemy / 无 |
| 环境管理 | python-dotenv + .env 文件 |

方案差异化原则：
- 方案 1：最适合该行业和团队（推荐）
- 方案 2：轻量替代（更少依赖，适合快速启动）
- 方案 3：企业级（更多工具，适合大团队）— 仅在 team_size > "3-5人" 时生成

### 阶段 4：行业特定配置

为每个方案附加行业特定的测试策略：

| 行业 | 特定策略 |
|------|---------|
| 金融/银行 | 幂等性断言、交易一致性检查、敏感数据脱敏验证、审计日志断言 |
| 医疗/健康 | HIPAA 合规字段检查、PHI 数据脱敏、访问控制矩阵测试 |
| 电商/零售 | 库存一致性、价格计算精度、并发下单幂等性、促销规则验证 |
| 互联网/SaaS | 多租户隔离、API 版本兼容性、限流测试、Webhook 回调验证 |
| 其他 | 通用 REST API 最佳实践 |

## 输出

写入 `.tide/research-report.json`：

```json
{
  "researched_at": "<ISO 时间戳>",
  "industry_profile": {
    "domain": "<industry>",
    "system_type": "<system_type>",
    "team_size": "<team_size>",
    "auth_complexity": "<auth_complexity>",
    "special_needs": ["<...>"]
  },
  "industry_context": {
    "key_concerns": ["数据安全", "幂等性", "审计日志"],
    "compliance": ["等保三级", "数据脱敏"],
    "references": [
      {"title": "...", "url": "...", "relevance": "HIGH"}
    ]
  },
  "recommended_solutions": [
    {
      "name": "方案名称",
      "summary": "一句话总结",
      "recommended": true,
      "stack": {
        "framework": "pytest",
        "http_client": "httpx",
        "report": "allure",
        "mock": "wiremock",
        "ci": "github_actions",
        "data_management": "factory_boy",
        "db_validation": "pymysql",
        "env_management": "python-dotenv"
      },
      "pros": ["..."],
      "cons": ["..."],
      "fit_score": 85,
      "industry_specific": [
        "金融交易幂等性断言",
        "敏感数据字段脱敏验证"
      ]
    }
  ]
}
```

写出后打印调研摘要：

```
行业调研完成
  行业：        <industry>
  调研来源：    <N> 篇文章
  推荐方案数：  <N> 个
  最佳方案：    <name>（适合度 <fit_score>/100）
```

## 错误处理

- 若 WebSearch 失败或无结果，基于内置知识给出推荐，并标注 `confidence: "low"`。
- 若行业不在已知列表中，使用通用 REST API 测试最佳实践。
- 每个方案的 `fit_score` 必须基于调研证据，不可凭空编造。
```

- [ ] **Step 2: Commit**

```bash
git add agents/industry-researcher.md
git commit -m "feat: 新增 industry-researcher Agent 定义 — 网络调研行业自动化最佳实践"
```

---

## Task 3: 创建行业断言规范文档

**Files:**
- Create: `prompts/industry-assertions.md`

- [ ] **Step 1: 创建 industry-assertions.md**

```markdown
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

| 场景类型 | 触发条件 | 说明 |
|---------|---------|------|
| `idempotency` | POST/PUT 写入类接口 | 相同请求发两次，第二次应返回幂等响应 |
| `audit_log` | 所有写入类接口 | 操作完成后审计日志表应有对应记录 |
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

| 场景类型 | 触发条件 | 说明 |
|---------|---------|------|
| `phi_masking` | 响应包含患者姓名/诊断/病历号 | PHI 字段应脱敏或按权限控制 |
| `access_control` | 所有患者数据接口 | 不同角色看到不同范围的数据 |
| `consent_check` | 数据共享/导出接口 | 操作前应检查患者知情同意状态 |

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

| 场景类型 | 触发条件 | 说明 |
|---------|---------|------|
| `inventory_consistency` | 下单/退货接口 | 操作前后库存数量应一致变化 |
| `price_precision` | 涉及金额计算的接口 | 金额应精确到分，无浮点精度问题 |
| `concurrent_order` | 下单接口 | 并发下单不应超卖 |

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

| 场景类型 | 触发条件 | 说明 |
|---------|---------|------|
| `tenant_isolation` | 多租户系统的数据接口 | 租户 A 不应看到租户 B 的数据 |
| `rate_limit` | 公开 API 接口 | 超过限流阈值应返回 429 |
| `version_compat` | 多版本 API 共存 | v1 和 v2 接口应各自返回正确格式 |

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
```

- [ ] **Step 2: Commit**

```bash
git add prompts/industry-assertions.md
git commit -m "feat: 新增行业特定断言规范 — 金融/医疗/电商/SaaS 四大行业"
```

---

## Task 4: 创建 tide-config.yaml Jinja2 模板

**Files:**
- Create: `templates/tide-config.yaml.j2`

- [ ] **Step 1: 创建模板文件**

```yaml
# tide-config.yaml — 由 /using-tide 自动生成
# 此文件记录项目配置，供 /tide 全流程读取

project:
  type: {{ project_type }}  # existing | new
  test_dir: {{ test_dir | default("tests") }}
  test_types:
{%- for t in test_types %}
    - {{ t }}
{%- endfor %}

{%- if project_type == "existing" %}
  code_style:
    api_pattern: {{ code_style.api_pattern | default("inline") }}
{%- if code_style.api_pattern_path %}
    api_pattern_path: {{ code_style.api_pattern_path }}
{%- endif %}
    request_class: {{ code_style.request_class | default("httpx") }}
{%- if code_style.request_class_path %}
    request_class_path: {{ code_style.request_class_path }}
{%- endif %}
    assertion_style: "{{ code_style.assertion_style | default('assert resp.status_code == 200') }}"
    auth_method: {{ code_style.auth_method | default("cookie") }}
{%- if code_style.auth_class %}
    auth_class: {{ code_style.auth_class }}
    auth_class_path: {{ code_style.auth_class_path }}
{%- endif %}
    allure_enabled: {{ code_style.allure_enabled | default(true) | lower }}
  package_manager: {{ package_manager | default("uv") }}
{%- endif %}

{%- if industry %}
industry:
  domain: "{{ industry.domain }}"
  system_type: "{{ industry.system_type }}"
  team_size: "{{ industry.team_size }}"
  auth_complexity: {{ industry.auth_complexity }}
  special_needs:
{%- for need in industry.special_needs | default([]) %}
    - {{ need }}
{%- endfor %}
  compliance:
{%- for c in industry.compliance | default([]) %}
    - "{{ c }}"
{%- endfor %}
{%- endif %}

{%- if solution %}
solution:
  name: "{{ solution.name }}"
  fit_score: {{ solution.fit_score }}
  stack:
    framework: {{ solution.stack.framework }}
    http_client: {{ solution.stack.http_client }}
    report: {{ solution.stack.report }}
    mock: {{ solution.stack.mock | default("none") }}
    ci: {{ solution.stack.ci | default("none") }}
    data_management: {{ solution.stack.data_management | default("none") }}
  industry_specific:
{%- for item in solution.industry_specific | default([]) %}
    - "{{ item }}"
{%- endfor %}
{%- endif %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/tide-config.yaml.j2
git commit -m "feat: 新增 tide-config.yaml Jinja2 模板"
```

---

## Task 5: 重写 skills/using-tide/SKILL.md

这是核心任务。完整重写初始化流程，实现第零步智能分类 + 分支 A/B + 共用步骤 + 配置验证。

**Files:**
- Modify: `skills/using-tide/SKILL.md` (complete rewrite)

- [ ] **Step 1: 重写 SKILL.md 完整内容**

将 `skills/using-tide/SKILL.md` 完整替换为以下内容：

````markdown
---
name: using-tide
description: "初始化 Tide 环境 — 智能项目分类、深度扫描/行业调研、方案推荐、脚手架生成。适用场景：首次运行、/using-tide、'初始化 tide'、'设置 tide'。"
argument-hint: "[--force]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, WebSearch, WebFetch
---

# Tide 初始化技能

为新项目或已有项目引导安装 Tide 自动化测试框架。
流程包括：环境校验、智能分类、深度扫描/行业调研、仓库接入、连接配置，
最终生成项目脚手架和 CLAUDE.md。

---

## 第零步：环境检测 + 智能分类

### 环境检测

检查所有必要工具是否可用：

```bash
python3 --version   # 要求 >= 3.12
uv --version        # 要求 uv 包管理器
git --version       # 要求 git
```

检测包管理器类型：

```bash
test -f uv.lock && echo "PKG_MGR: uv"
test -f poetry.lock && echo "PKG_MGR: poetry"
test -f requirements.txt && echo "PKG_MGR: pip"
```

检测插件依赖：

```bash
python3 -c "import jinja2" 2>/dev/null || echo "MISSING: jinja2"
python3 -c "import pydantic" 2>/dev/null || echo "MISSING: pydantic"
python3 -c "import yaml" 2>/dev/null || echo "MISSING: pyyaml"
```

若有缺失依赖，根据检测到的包管理器自动安装。

输出状态表格：

| 工具      | 要求版本 | 检测版本 | 状态 |
|-----------|----------|----------|------|
| Python    | >= 3.12  | x.y.z    | 正常/失败 |
| uv        | 任意     | x.y.z    | 正常/失败 |
| git       | 任意     | x.y.z    | 正常/失败 |
| jinja2    | 任意     | —        | 正常/已安装 |
| pydantic  | 任意     | —        | 正常/已安装 |
| pyyaml    | 任意     | —        | 正常/已安装 |

若有必要工具缺失，打印安装说明并终止。

### 快速重初始化检测

```bash
test -f tide-config.yaml && echo "CONFIG_EXISTS"
```

若 `tide-config.yaml` 已存在：

```
AskUserQuestion(
  "检测到已有 Tide 配置。请选择处理方式：",
  options=[
    "使用现有配置直接进入 /tide（推荐）",
    "更新配置（只修改变更项）",
    "完全重新初始化"
  ]
)
```

- 选择「使用现有配置」→ 打印"配置无变更，请运行 /tide <har-path>"并终止
- 选择「更新配置」→ 读取现有配置，后续步骤中只询问用户想修改的部分
- 选择「完全重新初始化」→ 备份现有配置到 `.tide/backup/`，继续完整流程

### 智能分类

扫描项目标志，判定项目类型：

```bash
# 计算测试文件数
TEST_COUNT=0
for d in testcases tests test; do
  if [ -d "$d" ]; then
    count=$(find "$d" -name "test_*.py" -o -name "*_test.py" 2>/dev/null | wc -l)
    TEST_COUNT=$((TEST_COUNT + count))
  fi
done
echo "TEST_FILE_COUNT: $TEST_COUNT"

# 检测 conftest.py
for f in conftest.py tests/conftest.py testcases/conftest.py test/conftest.py; do
  test -s "$f" && echo "CONFTEST: $f"
done

# 检测 pytest 配置
grep -q "\[tool\.pytest" pyproject.toml 2>/dev/null && echo "PYTEST_CONFIG: pyproject.toml"
test -f pytest.ini && echo "PYTEST_CONFIG: pytest.ini"
grep -q "\[tool:pytest\]" setup.cfg 2>/dev/null && echo "PYTEST_CONFIG: setup.cfg"

# 检测 HTTP 客户端
grep -rl "import requests\|import httpx\|BaseRequests" testcases/ tests/ test/ 2>/dev/null | head -3

# 检测 allure
grep -rl "import allure" testcases/ tests/ test/ 2>/dev/null | head -3

# 检测 CI 配置
test -d .github/workflows && echo "CI: github_actions"
test -f .gitlab-ci.yml && echo "CI: gitlab_ci"
test -f Jenkinsfile && echo "CI: jenkins"
```

**判定规则：**

```
if TEST_FILE_COUNT >= 3 AND (CONFTEST存在 OR PYTEST_CONFIG存在):
    project_type = "existing_auto"
else:
    project_type = "new"
```

输出分类结果：

```
项目类型判定：<existing_auto | new>
  测试文件数：<N>
  conftest：  <路径 | 未检测到>
  pytest 配置：<路径 | 未检测到>
```

**边界情况处理：**

- 若 `project_type = "new"` 但 `TEST_FILE_COUNT > 0`（1-2 个文件）：
  ```
  "注意：检测到 <N> 个测试文件，但不足以判定为自动化项目。
   如需保留这些文件，请在后续步骤中告知。"
  ```
- 若检测到非 Python 测试代码（.java/.js/.ts 测试文件）：
  ```
  "注意：检测到非 Python 测试代码，Tide 目前仅支持 Python 自动化测试。"
  ```

根据 `project_type` 进入对应分支。

---

## 分支 A：已有自动化项目（project_type = "existing_auto"）

### 第一步：深度扫描 Agent

启动 project-scanner Agent 深度分析项目：

```
Agent(
  name="project-scanner",
  description="深度扫描已有自动化项目，输出 7 维度分析",
  model="opus",
  prompt="
    读取 agents/project-scanner.md 中的完整指令。
    project_root: <当前目录>
    incremental: <true | false>
    last_commit: <.tide/project-profile.json 中的 scan_commit，若存在>
    执行全部 7 个维度的扫描，写入 .tide/project-profile.json。
  "
)
```

等待 Agent 完成，读取 `.tide/project-profile.json`。

### 第一步续：交互式逐项确认

读取 project-profile.json，按 7 个维度逐项向用户展示并确认。

**维度 1：项目架构**

```
AskUserQuestion(
  "【1/7 项目架构】检测结果：\n"
  "  测试入口目录：  <test_entry_dir>\n"
  "  子目录结构：    <subdirs 列表>\n"
  "  conftest 层级：  <conftest_levels>\n"
  "  工具类目录：    <utility_dirs>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

若用户选择"需要修正"，在 Other 中获取修正内容，更新 profile。

**维度 2：代码风格**

```
AskUserQuestion(
  "【2/7 代码风格】检测结果：\n"
  "  API 封装：      <api_pattern> (<api_pattern_path>)\n"
  "  Request 封装：  <request_class> (<request_class_path>)\n"
  "  断言风格：      <assertion_style>\n"
  "  命名规范：      <naming_convention>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

**维度 3：鉴权方式**

```
AskUserQuestion(
  "【3/7 鉴权方式】检测结果：\n"
  "  认证方式：      <auth_method>\n"
  "  认证类：        <auth_class> (<auth_class_path>)\n"
  "  多环境 Token：  <multi_env_token>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

**维度 4：依赖与工具链**

```
AskUserQuestion(
  "【4/7 依赖与工具链】检测结果：\n"
  "  Python 版本：   <python_version>\n"
  "  包管理器：      <package_manager>\n"
  "  HTTP 客户端：   <http_client> <http_client_version>\n"
  "  测试框架：      <test_framework>\n"
  "  Linter：        <linter>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

**维度 5：Allure 使用模式**

```
AskUserQuestion(
  "【5/7 Allure 标注】检测结果：\n"
  "  装饰器层级：    <decorator_hierarchy>\n"
  "  步骤模式使用率：<step_usage_ratio>\n"
  "  严重等级标注率：<severity_usage_ratio>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

**维度 6：数据管理模式**

```
AskUserQuestion(
  "【6/7 数据管理】检测结果：\n"
  "  测试数据来源：  <data_sources>\n"
  "  数据驱动：      <parametrize_count> 处 parametrize\n"
  "  数据库操作：    <db_helper_class> (<db_helper_path>)\n"
  "  清理策略：      <cleanup_strategy>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

**维度 7：行业与业务上下文**

```
AskUserQuestion(
  "【7/7 行业上下文】以下是 AI 从代码推断的信息：\n"
  "  推断行业：      <inferred_industry>\n"
  "  核心业务领域：  <business_domains>\n"
  "  合规要求：      <compliance_detected>\n"
  "\n是否正确？如有补充请在 Other 中说明。",
  options=["正确", "需要补充"]
)
```

将所有确认/修正后的结果作为 `_confirmed_profile` 存储，供后续步骤使用。

分支 A 完成后，跳转到第三步。

---

## 分支 B：新项目 / 非自动化项目（project_type = "new"）

### 第一步：行业画像收集

通过 5 个问题逐一收集用户行业画像：

**Q1 — 行业领域**

```
AskUserQuestion(
  "你所在的行业/领域是什么？",
  options=[
    "互联网/SaaS",
    "金融/银行/保险",
    "医疗/健康",
    "电商/零售"
  ]
)
```

**Q2 — 被测系统类型**

```
AskUserQuestion(
  "你要测试的系统属于什么类型？",
  options=[
    "Web 后端 API (REST/GraphQL)",
    "微服务架构（多服务间通信）",
    "移动端 BFF (Backend for Frontend)",
    "开放平台/第三方 API 集成"
  ]
)
```

**Q3 — 团队规模与自动化经验**

```
AskUserQuestion(
  "测试团队规模和自动化经验如何？",
  options=[
    "1-2 人，刚开始做自动化",
    "3-5 人，有一定自动化基础",
    "5+ 人，成熟的自动化体系"
  ]
)
```

**Q4 — 特殊需求**（多选）

```
AskUserQuestion(
  multiSelect=true,
  "项目有以下哪些特殊需求？",
  options=[
    "多环境切换 (dev/staging/prod)",
    "多版本 API 共存 (v1/v2/v3)",
    "国际化/多语言",
    "性能测试/压力测试"
  ]
)
```

**Q5 — 鉴权复杂度**

```
AskUserQuestion(
  "系统的鉴权方式有多复杂？",
  options=[
    "简单 — 单一 Cookie/Token",
    "中等 — 多角色权限 + RBAC",
    "复杂 — OAuth2/SSO/多租户",
    "不确定 — 需要调研"
  ]
)
```

将 5 个答案组装为 `_industry_profile`。

### 第二步：调研 Agent

派出 industry-researcher Agent：

```
Agent(
  name="industry-researcher",
  description="调研行业自动化测试最佳实践",
  model="sonnet",
  prompt="
    读取 agents/industry-researcher.md 中的完整指令。
    用户行业画像：
      industry: <Q1 答案>
      system_type: <Q2 答案>
      team_size: <Q3 答案>
      special_needs: <Q4 答案列表>
      auth_complexity: <Q5 答案>
    执行完整调研流程，写入 .tide/research-report.json。
  "
)
```

等待 Agent 完成，读取 `.tide/research-report.json`。

### 第二步续：方案呈现与选择

读取 research-report.json，向用户展示方案：

```
AskUserQuestion(
  "基于你的行业画像，以下是 AI 调研推荐的方案：\n\n"
  "━━━ 方案 1：<name>（推荐，适合度 <fit_score>/100）━━━\n"
  "  测试框架：<framework>\n"
  "  HTTP 客户端：<http_client>\n"
  "  报告：<report>\n"
  "  Mock：<mock>\n"
  "  CI/CD：<ci>\n"
  "  数据管理：<data_management>\n"
  "  行业特性：<industry_specific 列表>\n"
  "  优势：<pros>\n"
  "  劣势：<cons>\n\n"
  "━━━ 方案 2：<name>（适合度 <fit_score>/100）━━━\n"
  "  ...\n\n"
  // 方案 3 仅在有 3 个方案时显示
  "请选择一个方案：",
  options=["方案 1（推荐）", "方案 2", "方案 3"]  // 动态生成
)
```

将选择的方案存为 `_selected_solution`。

### 第二步续：方案试运行

基于选定方案，生成一个最小示例测试文件：

1. 根据 `industry_specific` 选取最具代表性的接口类型
2. 生成包含 1 个 GET + 1 个 POST 测试的文件
3. 展示给用户确认

```
AskUserQuestion(
  "以下是基于所选方案生成的示例测试文件。\n"
  "请确认代码风格是否符合预期：\n\n"
  "<示例代码内容>\n\n",
  options=[
    "风格正确，继续全量生成（推荐）",
    "需要调整"
  ]
)
```

若需调整，在 Other 中获取反馈后修改方案参数。

分支 B 完成后，继续第三步。

---

## 第三步：源码仓库配置（两个分支共用）

询问一个或多个待克隆的源码仓库 URL：

```
AskUserQuestion(
  "请输入源码仓库 URL（每行一个，可附加 @branch 后缀）：\n"
  "示例：\n"
  "  https://git.example.com/group1/backend.git\n"
  "  https://git.example.com/group2/api.git@develop\n"
  "输入完毕后留空回车。如不需要源码分析，请直接跳过。"
)
```

根据 URL 自动推导本地路径：

```
https://git.example.com/group1/repo1.git  →  .repos/group1/repo1/
```

克隆并切换每个仓库：

```bash
git clone <url> <local_path>
git -C <local_path> checkout <branch>   # 若指定了分支
```

询问 URL 前缀与仓库的映射关系：

```
AskUserQuestion(
  "请配置 URL 前缀与仓库的映射（每行一条）：\n"
  "格式：<url-prefix> → <repo-name>\n"
  "示例：\n"
  "  /api/v1 → backend\n"
  "  /admin  → admin-portal\n"
  "输入完毕后留空回车。"
)
```

若分支 B 的方案包含 Mock 服务：

```
AskUserQuestion(
  "所选方案包含 Mock 服务（<mock 名称>）。是否需要配置 Mock 服务仓库？",
  options=["是，输入 Mock 仓库 URL", "否，暂不配置"]
)
```

在项目根目录生成 `repo-profiles.yaml`：

```yaml
# repo-profiles.yaml — 由 /using-tide 自动生成
repos:
  - name: <repo-name>
    local_path: .repos/<group>/<repo>/
    remote: <url>
    branch: <branch>
    url_prefixes:
      - <prefix1>
      - <prefix2>
```

---

## 第四步：连接配置（两个分支共用，深度按鉴权复杂度分级）

询问被测系统的 Base URL：

```
AskUserQuestion(
  "请输入目标系统的 Base URL（例如：http://172.16.115.247）："
)
```

询问认证方式。根据分支和鉴权复杂度动态调整选项：

**分支 A（检测到认证逻辑时）：**

```
AskUserQuestion(
  "请选择认证方式：",
  options=[
    "复用旧项目认证逻辑（推荐，检测到：<auth_class>）",
    "Cookie（粘贴原始 Cookie 请求头值）",
    "Token（Bearer token）",
    "用户名 + 密码",
    "无需认证"
  ]
)
```

**分支 B（简单鉴权）：**

```
AskUserQuestion(
  "请选择认证方式：",
  options=[
    "Cookie（粘贴原始 Cookie 请求头值）",
    "Token（Bearer token）",
    "用户名 + 密码",
    "无需认证"
  ]
)
```

**分支 B（中等鉴权 — RBAC）：** 上述选项 + 额外追问：

```
AskUserQuestion(
  "请输入需要测试的角色列表（每行一个）：\n"
  "示例：admin, editor, viewer"
)
```

**分支 B（复杂鉴权 — OAuth2/SSO）：** 上述选项 + 额外追问：

```
AskUserQuestion("请输入 OAuth2 Client ID：")
AskUserQuestion("请输入 OAuth2 Client Secret：")
AskUserQuestion("请输入 SSO/Token 端点 URL：")
```

根据所选方式逐项收集凭证。若选择「复用旧项目认证逻辑」，记录 `auth_method: reuse`。

询问可选集成项（同现有流程）：

```
AskUserQuestion("是否配置数据库连接？（y/n）")
```

若选是，逐项收集数据库字段。

```
AskUserQuestion("是否配置通知 Webhook？（y/n）\n支持：钉钉、飞书、Slack")
```

若选是，询问 Webhook URL 和平台类型。

### 配置文件写入

**分支 A（已有 .env）：** 不修改 .env，Tide 配置写入 `.tide/config.yaml`。

**分支 B（新项目）：** 正常写入 `.env` 和 `.env.example`。

---

## 第五步：脚手架生成 + CLAUDE.md + 配置验证

### 生成 tide-config.yaml

使用 Jinja2 模板 `templates/tide-config.yaml.j2` 渲染 `tide-config.yaml`：
- 分支 A：包含 `project.code_style` 段（从确认后的 profile 提取）
- 分支 B：包含 `industry` 段和 `solution` 段

### 脚手架生成

**分支 A：**

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/scaffold.py \
  --mode existing \
  --project-root "."
```

仅追加 `.tide/`、`.repos/`、`.trash/` 目录和 `.gitignore` 条目。

**分支 B：**

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/scaffold.py \
  --mode new \
  --stack "${_selected_solution.stack}" \
  --base-url "${BASE_URL}" \
  --project-root "."
```

生成完整目录结构：tests/、core/、conftest.py、pyproject.toml、Makefile 等。

### 生成 CLAUDE.md

在项目根目录生成 `CLAUDE.md`：

**分支 A 的 CLAUDE.md 包含：**
```markdown
# CLAUDE.md — Tide 项目（已有项目适配）

## 项目理解
<7 维度扫描确认后的摘要>

## 代码风格约束
- API 封装：<api_pattern>
- Request 封装：<request_class>
- 断言风格：<assertion_style>
- 认证方式：<auth_method>
以上风格优先于 Tide 默认规范。

## 行业上下文
<维度 7 确认结果>
```

**分支 B 的 CLAUDE.md 包含：**
```markdown
# CLAUDE.md — Tide 项目

## 技术栈
<选定方案的完整技术栈>

## 行业上下文
<行业画像 + 合规要求>

## 项目结构
<目录树>

## 环境信息
- Base URL：${BASE_URL}
- 认证方式：<method>
- 数据库：<已配置 / 未配置>
```

### 配置验证

在脚手架生成后，自动执行 smoke test：

```bash
# 1. Base URL 可达性
python3 -c "
import httpx
try:
    r = httpx.get('${BASE_URL}', timeout=10)
    print(f'BASE_URL: OK (HTTP {r.status_code})')
except Exception as e:
    print(f'BASE_URL: FAIL ({e})')
"
```

```bash
# 2. 认证有效性（若非 reuse 模式）
python3 -c "
import httpx
headers = {<根据认证方式构建>}
try:
    r = httpx.get('${BASE_URL}', headers=headers, timeout=10)
    print(f'AUTH: {\"OK\" if r.status_code < 400 else \"FAIL\"} (HTTP {r.status_code})')
except Exception as e:
    print(f'AUTH: FAIL ({e})')
"
```

```bash
# 3. 数据库连接（若配置了数据库）
python3 -c "
import pymysql
try:
    conn = pymysql.connect(host='${DB_HOST}', port=${DB_PORT}, user='${DB_USER}', password='${DB_PASS}', database='${DB_NAME}')
    print('DB: OK')
    conn.close()
except Exception as e:
    print(f'DB: FAIL ({e})')
"
```

展示验证结果：

```
配置验证结果：
  Base URL 可达性：  <通过/失败 + 详情>
  认证有效性：        <通过/失败 + 详情>
  数据库连接：        <通过/失败/未配置>
```

若有失败项：

```
AskUserQuestion(
  "<失败项> 验证失败：<错误详情>\n是否立即修正？",
  options=["是，重新输入", "跳过，稍后修正"]
)
```

若选择修正，回到第四步对应的配置项重新收集。

### 打印初始化摘要

```
Tide 初始化完成
──────────────────────────────────────────
项目类型：      <existing_auto / new>
技术栈：        <方案名称 / 旧项目原有栈>
行业：          <domain>
已克隆仓库：    <N> 个
URL 映射：      <N> 条
认证方式：      <method>
数据库：        <已配置 / 未配置>
配置验证：      <全部通过 / N 项失败>
──────────────────────────────────────────
下一步：执行 /tide <path-to.har>
```
````

- [ ] **Step 2: Commit**

```bash
git add skills/using-tide/SKILL.md
git commit -m "feat: 重写 /using-tide — 智能分类 + 深度扫描/行业调研 + 方案推荐 + 配置验证"
```

---

## Task 6: 修改 skills/tide/SKILL.md — 增加行业配置读取

**Files:**
- Modify: `skills/tide/SKILL.md:43-51` (预检阶段的"项目配置读取"部分)

- [ ] **Step 1: 在预检阶段增加行业配置读取**

在 `skills/tide/SKILL.md` 的"**2. 项目配置读取**"段落末尾追加行业配置读取逻辑。找到以下内容：

```
读取 `tide-config.yaml`（若存在），提取以下配置：
- `test_types` — 用户选择的测试类型列表（如 `["interface", "scenario"]`），默认为全部类型
```

替换为：

```
读取 `tide-config.yaml`（若存在），提取以下配置：
- `test_types` — 用户选择的测试类型列表（如 `["interface", "scenario"]`），默认为全部类型
- `industry` — 行业画像（若存在），提取 `domain`、`compliance`、`special_needs`
- `solution.industry_specific` — 行业特定测试策略列表
- `project.code_style` — 已有项目的代码风格配置（若 `project.type == "existing"`）

若 `industry` 段存在，设置 `industry_mode = true`，后续波次传递行业上下文给下游 Agent。
```

- [ ] **Step 2: 在波次 2 场景分析 Agent prompt 中传递行业上下文**

在 `skills/tide/SKILL.md` 中找到完整 prompt 的 scenario-analyzer Agent 调用（约第 264-303 行区域），在 prompt 末尾追加：

```

    若 industry_mode = true：
    同时读取：${CLAUDE_SKILL_DIR}/../../prompts/industry-assertions.md
    行业：<industry.domain>
    合规要求：<industry.compliance>
    行业特定策略：<solution.industry_specific>
    在生成场景时，为写入类接口追加行业特定场景类别。
```

- [ ] **Step 3: 在波次 3 代码生成 Agent prompt 中传递行业上下文**

在 `skills/tide/SKILL.md` 中找到 case-writer Agent 调用（约第 370-396 行区域），在 prompt 末尾追加：

```

    若 industry_mode = true：
    同时读取：${CLAUDE_SKILL_DIR}/../../prompts/industry-assertions.md
    行业：<industry.domain>
    在生成测试代码时，在标准 L1-L5 断言之后追加行业特定断言。
    行业断言标注格式：# Industry[<行业>]: <说明>
```

- [ ] **Step 4: Commit**

```bash
git add skills/tide/SKILL.md
git commit -m "feat: /tide 预检增加行业配置读取，波次 2/3 传递行业上下文"
```

---

## Task 7: 修改 agents/case-writer.md — 增加行业感知

**Files:**
- Modify: `agents/case-writer.md:23-52` (已有项目适配段落之后)

- [ ] **Step 1: 在"已有项目适配"段落后追加"行业感知断言"段落**

在 `agents/case-writer.md` 中找到"若 tide-config.yaml 不存在，使用默认的 httpx + pydantic 模式。"这行（第 52 行），在其后追加：

```markdown

## 行业感知断言

若任务 prompt 中指定了行业模式（`industry_mode = true`），必须读取 `prompts/industry-assertions.md`。

根据 `industry.domain` 的值，在每个测试方法的标准 L1-L5 断言之后，追加行业特定断言：

1. 读取 `prompts/industry-assertions.md` 中对应行业的"必须追加的场景类别"
2. 对写入类接口（POST/PUT/DELETE），检查是否需要幂等性/审计/脱敏断言
3. 在断言代码上方标注 `# Industry[<行业>]: <说明>`

若 `industry.domain` 不在已知行业列表中，或 `industry` 段不存在，跳过此段落。
```

- [ ] **Step 2: Commit**

```bash
git add agents/case-writer.md
git commit -m "feat: case-writer 增加行业感知断言生成规则"
```

---

## Task 8: 修改 agents/scenario-analyzer.md — 增加行业特定场景

**Files:**
- Modify: `agents/scenario-analyzer.md:47-61` (场景类型表格之后)

- [ ] **Step 1: 在场景类型表格后追加行业场景**

在 `agents/scenario-analyzer.md` 中找到场景类型表格（第 49-60 行区域），在 `| exception |` 行之后追加：

```markdown
| `industry_idempotency` | 写入类接口（行业模式 + 金融/电商）| 幂等性检查 — 重复提交应被拒绝 |
| `industry_audit` | 写入类接口（行业模式 + 金融）| 审计日志 — 操作应产生审计记录 |
| `industry_masking` | 响应含敏感字段（行业模式 + 金融/医疗）| 数据脱敏 — 敏感字段应部分隐藏 |
| `industry_isolation` | 多租户接口（行业模式 + SaaS）| 租户隔离 — 跨租户访问应被拒绝 |
```

- [ ] **Step 2: 在"阶段二：场景生成"段首追加行业模式说明**

在 `agents/scenario-analyzer.md` 的"以 `prompts/scenario-enrich.md` 为策略指南"这行之前，追加：

```markdown
若任务 prompt 中包含 `industry_mode = true`，同时读取 `prompts/industry-assertions.md`，为写入类接口追加上表中的 `industry_*` 类型场景。行业场景仅在对应行业匹配时生成。
```

- [ ] **Step 3: Commit**

```bash
git add agents/scenario-analyzer.md
git commit -m "feat: scenario-analyzer 增加行业特定场景类别"
```

---

## Task 9: 修改 agents/case-reviewer.md — 增加行业合规评审

**Files:**
- Modify: `agents/case-reviewer.md:17-72` (静态审查段落)

- [ ] **Step 1: 在"5. 可运行性"维度之后追加"6. 行业合规"维度**

在 `agents/case-reviewer.md` 中找到"### 5. 可运行性"段落的末尾（"标记：缺失导入、未定义 fixture、模型字段不匹配。"这行之后），追加：

```markdown

### 6. 行业合规（仅在 tide-config.yaml 中存在 industry 段时评估）

读取 `tide-config.yaml` 中的 `industry.domain`，并读取 `prompts/industry-assertions.md`。

检查每个测试文件：
- 写入类接口（POST/PUT/DELETE）是否包含行业必须的场景？
- 行业断言的标注格式是否正确（`# Industry[<行业>]: <说明>`）？
- 行业断言逻辑是否正确（如幂等性检查是否真正发了两次请求）？

标记：缺少行业必须场景（MEDIUM）、行业断言逻辑错误（HIGH）。

若 `industry` 段不存在，此维度评分为 N/A，不计入偏差率。
```

- [ ] **Step 2: 更新维度评分输出格式**

在 case-reviewer.md 的输出报告模板中（"审查评分"段），在 `可运行性` 之后追加：

```
    行业合规:      <分数>/100 | N/A
```

- [ ] **Step 3: Commit**

```bash
git add agents/case-reviewer.md
git commit -m "feat: case-reviewer 增加行业合规评审维度"
```

---

## Task 10: 修改 prompts/code-style-python.md — 增加行业规则引用

**Files:**
- Modify: `prompts/code-style-python.md:1-19` (已有项目风格优先规则段落)

- [ ] **Step 1: 在"已有项目风格优先规则"段落末尾追加行业规则引用**

在 `prompts/code-style-python.md` 中找到"**以上规则优先于本文档中的默认规范。**"这行（第 19 行），在其后追加：

```markdown

### 行业特定代码规则

当 `tide-config.yaml` 中存在 `industry.domain` 字段时，还需遵循 `prompts/industry-assertions.md` 中对应行业的断言规范。

优先级：已有项目风格 > 行业特定规则 > Tide 默认规范。
```

- [ ] **Step 2: Commit**

```bash
git add prompts/code-style-python.md
git commit -m "feat: code-style-python 增加行业规则引用"
```

---

## Task 11: 修改 scripts/scaffold.py — 支持 tide-config.yaml 生成

**Files:**
- Modify: `scripts/scaffold.py`

- [ ] **Step 1: 在 ScaffoldConfig 中增加 config_vars 字段**

在 `scripts/scaffold.py` 中找到 `ScaffoldConfig` 类（第 145-150 行），将其替换为：

```python
@dataclass(frozen=True)
class ScaffoldConfig:
    project_root: Path
    project_name: str
    base_url: str
    db_configured: bool = False
    config_vars: dict = field(default_factory=dict)
```

需要在文件顶部增加 `field` 导入：

```python
from dataclasses import dataclass, field
```

- [ ] **Step 2: 在 generate_project 函数中追加 tide-config.yaml 渲染**

在 `scripts/scaffold.py` 的 `generate_project` 函数中，找到"# 9. Makefile"段（第 264-265 行），在其后追加：

```python
    # 10. tide-config.yaml（若有配置变量）
    if config.config_vars:
        tide_config_template = TEMPLATES_DIR / "tide-config.yaml.j2"
        if tide_config_template.exists():
            config_content = env.get_template("tide-config.yaml.j2").render(**config.config_vars)
            if _write_if_not_exists(root / "tide-config.yaml", config_content):
                created.append("tide-config.yaml")
```

- [ ] **Step 3: 在 append_to_existing_project 函数中追加 tide-config.yaml 渲染**

在 `scripts/scaffold.py` 的 `append_to_existing_project` 函数末尾（`return created` 之前），追加：

```python
    # 3. tide-config.yaml（若有配置变量）
    if config.config_vars:
        config_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), keep_trailing_newline=True)
        tide_config_template = TEMPLATES_DIR / "tide-config.yaml.j2"
        if tide_config_template.exists():
            config_content = config_env.get_template("tide-config.yaml.j2").render(**config.config_vars)
            if _write_if_not_exists(root / "tide-config.yaml", config_content):
                created.append("tide-config.yaml")
```

- [ ] **Step 4: Commit**

```bash
git add scripts/scaffold.py
git commit -m "feat: scaffold.py 支持 tide-config.yaml 模板渲染"
```

---

## Task 12: 使用 cli-anything-drawio 重绘工作流程图

**Files:**
- Modify: `assets/workflow.drawio` (重新生成)
- Modify: `assets/workflow.png` (从 .drawio 导出)

- [ ] **Step 1: 安装 cli-anything-drawio（若未安装）**

```bash
cd /Users/poco/Projects/CLI-Anything/drawio/agent-harness && pip install -e . 2>/dev/null; which cli-anything-drawio
```

- [ ] **Step 2: 创建新的 workflow.drawio**

```bash
cd /Users/poco/Projects/tide
cli-anything-drawio project new --preset 16:9 -o assets/workflow.drawio
```

- [ ] **Step 3: 绘制第零步 — 环境检测 + 智能分类**

```bash
P="assets/workflow.drawio"
D="cli-anything-drawio --project $P"

# 标题
$D shape add text --label "Tide 工作流总览" --x 340 --y 20 -w 300 -h 40
$D shape style v_1 fontSize 24
$D shape style v_1 fontStyle 1

# 第零步
$D shape add rounded --label "第零步：环境检测 + 智能分类" --x 300 --y 80 -w 380 -h 50
$D shape style v_2 fillColor "#e1d5e7"
$D shape style v_2 strokeColor "#9673a6"
$D shape style v_2 fontSize 14

# 判断菱形
$D shape add diamond --label "项目类型？" --x 400 --y 160 -w 180 -h 80
$D shape style v_3 fillColor "#fff2cc"
$D shape style v_3 strokeColor "#d6b656"
```

- [ ] **Step 4: 绘制分支 A — 已有自动化项目**

```bash
# 分支 A 标题
$D shape add rounded --label "分支 A：已有自动化项目" --x 80 --y 280 -w 280 -h 40
$D shape style v_4 fillColor "#d5e8d4"
$D shape style v_4 strokeColor "#82b366"
$D shape style v_4 fontSize 12

# project-scanner Agent
$D shape add rounded --label "project-scanner Agent\n（opus · 7 维度扫描）" --x 80 --y 340 -w 280 -h 50
$D shape style v_5 fillColor "#d5e8d4"
$D shape style v_5 strokeColor "#82b366"

# 交互式确认
$D shape add rounded --label "交互式逐项确认\n（7 个 AskUserQuestion）" --x 80 --y 410 -w 280 -h 50
$D shape style v_6 fillColor "#d5e8d4"
$D shape style v_6 strokeColor "#82b366"
```

- [ ] **Step 5: 绘制分支 B — 新项目**

```bash
# 分支 B 标题
$D shape add rounded --label "分支 B：新项目 / 非自动化" --x 620 --y 280 -w 280 -h 40
$D shape style v_7 fillColor "#dae8fc"
$D shape style v_7 strokeColor "#6c8ebf"
$D shape style v_7 fontSize 12

# 行业画像
$D shape add rounded --label "行业画像收集\n（5 个问题）" --x 620 --y 340 -w 280 -h 50
$D shape style v_8 fillColor "#dae8fc"
$D shape style v_8 strokeColor "#6c8ebf"

# industry-researcher Agent
$D shape add rounded --label "industry-researcher Agent\n（sonnet · WebSearch）" --x 620 --y 410 -w 280 -h 50
$D shape style v_9 fillColor "#dae8fc"
$D shape style v_9 strokeColor "#6c8ebf"

# 方案选择
$D shape add rounded --label "2-3 方案推荐 + 试运行" --x 620 --y 480 -w 280 -h 50
$D shape style v_10 fillColor "#dae8fc"
$D shape style v_10 strokeColor "#6c8ebf"
```

- [ ] **Step 6: 绘制共用步骤 + /tide 4 波次**

```bash
# 合流点
$D shape add rounded --label "第三步：源码仓库配置" --x 300 --y 570 -w 380 -h 40
$D shape style v_11 fillColor "#f8cecc"
$D shape style v_11 strokeColor "#b85450"

$D shape add rounded --label "第四步：连接配置（按鉴权分级）" --x 300 --y 630 -w 380 -h 40
$D shape style v_12 fillColor "#f8cecc"
$D shape style v_12 strokeColor "#b85450"

$D shape add rounded --label "第五步：脚手架 + CLAUDE.md + 配置验证" --x 300 --y 690 -w 380 -h 40
$D shape style v_13 fillColor "#f8cecc"
$D shape style v_13 strokeColor "#b85450"

# /tide 入口
$D shape add rounded --label "/tide <har-path>" --x 350 --y 770 -w 280 -h 50
$D shape style v_14 fillColor "#e1d5e7"
$D shape style v_14 strokeColor "#9673a6"
$D shape style v_14 fontSize 14
$D shape style v_14 fontStyle 1

# 4 波次
$D shape add rounded --label "Wave 1：解析与准备（并行）\nhar-parser + repo-syncer" --x 80 --y 850 -w 200 -h 60
$D shape style v_15 fillColor "#fff2cc"
$D shape style v_15 strokeColor "#d6b656"

$D shape add rounded --label "Wave 2：场景分析\nscenario-analyzer\n+ 行业场景" --x 300 --y 850 -w 200 -h 60
$D shape style v_16 fillColor "#fff2cc"
$D shape style v_16 strokeColor "#d6b656"

$D shape add rounded --label "Wave 3：代码生成\ncase-writer ×N\n+ 行业断言" --x 520 --y 850 -w 200 -h 60
$D shape style v_17 fillColor "#fff2cc"
$D shape style v_17 strokeColor "#d6b656"

$D shape add rounded --label "Wave 4：评审与交付\ncase-reviewer\n+ 行业合规" --x 740 --y 850 -w 200 -h 60
$D shape style v_18 fillColor "#fff2cc"
$D shape style v_18 strokeColor "#d6b656"
```

- [ ] **Step 7: 添加连接线**

```bash
# 第零步 → 判断
$D connect add v_2 v_3

# 判断 → 分支 A
$D connect add v_3 v_4 --label "existing_auto"

# 判断 → 分支 B
$D connect add v_3 v_7 --label "new"

# 分支 A 内部
$D connect add v_4 v_5
$D connect add v_5 v_6

# 分支 B 内部
$D connect add v_7 v_8
$D connect add v_8 v_9
$D connect add v_9 v_10

# 合流
$D connect add v_6 v_11
$D connect add v_10 v_11

# 共用步骤
$D connect add v_11 v_12
$D connect add v_12 v_13
$D connect add v_13 v_14

# /tide → 4 波次
$D connect add v_14 v_15
$D connect add v_15 v_16
$D connect add v_16 v_17
$D connect add v_17 v_18
```

- [ ] **Step 8: 导出 PNG**

```bash
cli-anything-drawio --project assets/workflow.drawio export render assets/workflow.png -f png --overwrite
```

- [ ] **Step 9: Commit**

```bash
git add assets/workflow.drawio assets/workflow.png
git commit -m "feat: 使用 cli-anything-drawio 重绘工作流程图 — 初始化分支 + 行业感知"
```

---

## Task 13: 更新 README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新版本徽章**

找到 `Tide-1.1` 替换为 `Tide-1.2`。
找到 `version-1.1.0` 替换为 `version-1.2.0`。

- [ ] **Step 2: 更新核心特性表格**

找到核心特性表格（约第 60-69 行），在"旧项目无侵入"行之前插入 3 行：

```markdown
| **智能项目分类** | 自动检测已有自动化项目 vs 新项目，阈值保守、不误判覆盖 |
| **行业感知** | 收集行业画像 → AI 调研 → 2-3 方案推荐，行业断言全流程贯穿 |
| **方案推荐** | 基于行业/团队/鉴权复杂度，推荐完整技术方案（框架+CI+报告+Mock+数据管理） |
```

- [ ] **Step 3: 更新使用指南 > 步骤 1**

找到"### 步骤 1：初始化项目"（约第 204 行），将其后的表格替换为：

```markdown
交互式向导会根据项目类型自动选择路径：

**已有自动化项目（自动检测）：**

| 步骤 | 说明 |
|------|------|
| 环境检测 + 智能分类 | 自动判定为已有项目 |
| 深度扫描 (project-scanner) | opus Agent 通读项目代码，输出 7 维度分析 |
| 交互式确认 | 架构、代码风格、鉴权、工具链、Allure、数据管理、行业 — 逐项确认 |
| 仓库配置 | 输入后端仓库 URL，自动 clone + URL 前缀映射 |
| 连接配置 | Base URL · 认证（可复用旧项目逻辑）· 数据库 · 通知 |
| 配置验证 | 自动 smoke test：URL 可达 + 认证有效 + DB 连接 |

**新项目 / 非自动化项目：**

| 步骤 | 说明 |
|------|------|
| 环境检测 + 智能分类 | 自动判定为新项目 |
| 行业画像收集 | 行业、系统类型、团队规模、特殊需求、鉴权复杂度 |
| AI 调研 (industry-researcher) | sonnet Agent 网络搜索行业最佳实践 |
| 方案推荐 | 展示 2-3 个完整技术方案，用户选择 |
| 方案试运行 | 生成最小示例测试文件，确认风格后全量生成 |
| 仓库配置 + 连接配置 + 配置验证 | 同上 |
```

- [ ] **Step 4: 更新融入已有项目章节**

找到"## 融入已有项目"（约第 259 行），替换场景 A 和 B 的内容：

```markdown
## 融入已有项目

### 场景 A：全新项目

```bash
mkdir my-api-tests && cd my-api-tests && git init
# 在 Claude Code 中：/using-tide
```

向导会收集行业画像，AI 调研后推荐技术方案，试运行确认后生成完整脚手架。

### 场景 B：已有自动化项目

```bash
cd /path/to/existing-test-project
# 在 Claude Code 中：/using-tide
```

**向导会自动检测项目类型，派 Agent 深度扫描 7 个维度：**

| 维度 | 检测内容 |
|------|---------|
| 项目架构 | 测试入口目录、子目录结构、conftest 层级 |
| 代码风格 | API 封装模式、Request 工具类、断言风格 |
| 鉴权方式 | 认证类位置、Cookie/Token/OAuth2 |
| 依赖工具链 | Python 版本、包管理器、HTTP 客户端 |
| Allure 模式 | 装饰器层级、step 使用率 |
| 数据管理 | 数据来源、parametrize、清理策略 |
| 行业上下文 | AI 推断行业/领域、合规要求 |

每个维度逐项确认后写入配置。**原则：项目已有规范 > 行业规则 > 插件默认规范。**
```

- [ ] **Step 5: 更新配置参考 — 新增 tide-config.yaml industry 段**

找到"### tide-config.yaml"配置参考（约第 326 行），在现有示例之后追加：

```yaml

# 行业信息（由 /using-tide 自动生成）
industry:
  domain: "金融/银行"
  system_type: "微服务架构"
  team_size: "3-5人"
  auth_complexity: complex
  special_needs: ["multi_env"]
  compliance: ["等保三级", "数据脱敏"]

solution:
  name: "金融级 API 自动化方案"
  fit_score: 92
  stack:
    framework: pytest
    http_client: httpx
    report: allure
    mock: wiremock
    ci: github_actions
    data_management: factory_boy
  industry_specific:
    - "金融交易幂等性断言"
    - "敏感数据字段脱敏验证"
```

- [ ] **Step 6: 更新项目结构**

找到"## 项目结构"中的 agents 列表（约第 365 行），追加：

```
│   ├── project-scanner.md           #   项目深度扫描（opus）
│   └── industry-researcher.md       #   行业调研（sonnet）
```

在 prompts 列表中追加：

```
│   └── industry-assertions.md       #   行业特定断言规范
```

- [ ] **Step 7: 更新 Roadmap**

找到 Roadmap 表格（约第 409 行），更新 v1.2 行：

```markdown
| **v1.2**（当前） | 智能项目分类 · 7 维度深度扫描 · 行业画像与 AI 调研 · 方案推荐 · 配置验证 · 全流程行业感知 · 流程图重绘 |
```

将原来的 v1.1 行标记为历史版本（去掉"当前"标记）。

- [ ] **Step 8: Commit**

```bash
git add README.md
git commit -m "docs: 更新 README — 智能分类、行业感知、方案推荐、新流程图"
```

---

## Task 14: 最终验证

**Files:** 无新文件

- [ ] **Step 1: 检查所有新增文件存在**

```bash
ls -la agents/project-scanner.md agents/industry-researcher.md prompts/industry-assertions.md templates/tide-config.yaml.j2
```

Expected: 4 个文件全部存在。

- [ ] **Step 2: 检查所有修改文件的关键内容**

```bash
grep -l "industry" skills/using-tide/SKILL.md skills/tide/SKILL.md agents/case-writer.md agents/scenario-analyzer.md agents/case-reviewer.md prompts/code-style-python.md scripts/scaffold.py README.md
```

Expected: 8 个文件全部匹配。

- [ ] **Step 3: 验证 scaffold.py 语法正确**

```bash
cd /Users/poco/Projects/tide && python3 -m py_compile scripts/scaffold.py && echo "OK"
```

Expected: `OK`

- [ ] **Step 4: 验证流程图文件**

```bash
ls -la assets/workflow.drawio assets/workflow.png
```

Expected: 两个文件都存在且大小合理。

- [ ] **Step 5: Git log 检查**

```bash
git log --oneline -10
```

Expected: 看到本次重构的全部 commit。

- [ ] **Step 6: Commit 最终验证通过标记**

无需额外 commit，确认全部通过即可。
