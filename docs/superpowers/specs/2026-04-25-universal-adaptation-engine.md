# 通用适配引擎设计

## 概述

将 tide 从"固定模板生成"升级为"通用适配引擎"：安装后自动扫描目标项目的代码规范，生成的测试自动匹配项目现有的 API 引用方式、HTTP 客户端、断言风格、Allure 标注、测试数据结构等规范。

## 架构

```
/using-tide → convention_scanner.py (AST) → scout.json
                       ↓
               project-scanner (opus) → convention-fingerprint.yaml
                       ↓
               tide-config.yaml (引用 fingerprint 关键字段)
                       ↓
/tide → case-writer (sonnet) ← 读取 fingerprint → 生成匹配代码
```

## 核心组件

### 1. convention_scanner.py（新建）

脚本实现三层 AST 检测，不需要 AI 参与：

**第一层：文件结构扫描**
- 统计 testcases/ api/ utils/ 数量
- 检测测试文件命名模式（_test.py / test_*.py）
- 检测 API 目录下的文件模式
- 检测 conftest.py 分布
- 检测 pytest.ini / pyproject.toml / setup.cfg
- 检测 requirements.txt 中的关键依赖

**第二层：模式识别（AST 扫描）**
- `detect_api_pattern()` — API URL 模式检测：Enum / Dict / 常量 / 内联
- `detect_http_client()` — HTTP 客户端检测：requests/httpx/aiohttp/direct
- `detect_assertion_style()` — 断言风格检测：dict_get / bracket / attr / status_only
- `detect_allure_pattern()` — Allure 使用检测：级别、step 方式
- `detect_service_layer()` — Service 层检测：有/无/模式
- `detect_auth_method()` — 认证方式检测：cookie/token/basic/无
- `detect_test_data_pattern()` — 数据模式检测：inline/separated/fixture
- `detect_module_structure()` — 模块结构检测：single/multi_module

### 2. convention-fingerprint.yaml（新建输出文件）

由 project-scanner 在 scanner.py 输出结果基础上生成。结构：

```yaml
version: "1.0"
scanned_at: "ISO 时间戳"

api:
  pattern:
    type: enum                    # enum | dict | constant | inline
    class_pattern: "{Module}Api"
    value_access: ".value"
    url_prefix: "/api/rdos/"
  modules:
    - name: batch
      class: BatchApi
      location: api/batch/batch_api.py

http_client:
  library: requests
  client_pattern: session         # direct | session | custom_class
  custom_class: BaseRequests
  methods: [post, get, put, delete]

auth:
  method: cookie
  auth_class: BaseCookies

response:
  parse_method: json
  success_indicator:
    field: code
    expected: 1

assertion:
  style: dict_get
  common_checks:
    - "assert resp.get('code') == 1"

allure:
  enabled: true
  epic_level: true
  title_level: both
  step_pattern: context

test_data:
  pattern: separated
  data_dir: testdata
  mirror_structure: true

test_lifecycle:
  class_setup: setup_class
  method_setup: setup
  fixture_scope: session

service_layer:
  detected: true
  pattern: service_request

module_structure:
  isolation: multi_module
  modules: []
```

### 3. Case-Writer prompt 动态组装

修改 `skills/tide/SKILL.md` 预检阶段，在检测到 fingerprint 时注入额外约束：

```
当前模式：
  - 有 convention-fingerprint.yaml → 注入规范约束
  - 无 fingerprint → 使用通用默认指令
```

case-writer 收到 fingerprint 后输出的代码需要：
1. URL 引用 → 使用 fingerprint.api 中定义的枚举/字典
2. HTTP 调用 → 使用 fingerprint.http_client 中的封装类
3. 断言 → 使用 fingerprint.assertion 中的风格
4. Allure → 使用 fingerprint.allure 中的层级
5. 数据 → 使用 fingerprint.test_data 中的模式

### 4. 生成文件独立目录

生成的测试文件输出到独立位置，与手写测试隔离：
- `testcases/scenariotest/tide_generated/`
- 文件名：`test_tide_{module}_{timestamp}.py`
- 用户 review 后手动合并到正式目录

## 验证策略

1. **dtstack-httprunner** — 完整的真实企业项目，验证 scanner 检测准确性和生成代码兼容性
2. **白板项目** — 创建一个简单的 requests 直接调用项目，验证 inline 模式检测
3. **空项目** — 无现有测试的项目，验证降级到通用模式

## 文件变更

```
新建:
  scripts/convention_scanner.py     — AST 扫描脚本

修改:
  agents/project-scanner.md         — 增加 fingerprint 生成指令  
  prompts/code-style-python.md      — 增加 fingerprint 适配策略
  skills/tide/SKILL.md          — 预检加载 fingerprint 并注入 case-writer
  skills/using-tide/SKILL.md    — 扫描步骤增加 fingerprint 生成
```
