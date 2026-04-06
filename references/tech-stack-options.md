# 技术栈选型参考

本文档梳理 sisyphus-autoflow 生成的测试项目各层的可选技术方案，供 `/using-autoflow` 向导和人工决策参考。

---

## 目录

- [测试框架 + HTTP 客户端](#测试框架--http-客户端)
- [测试报告](#测试报告)
- [代码检查（Linting）](#代码检查)
- [类型检查](#类型检查)
- [总结推荐](#总结推荐)

---

## 测试框架 + HTTP 客户端

### 方案 A：pytest + httpx + pydantic（推荐）

| 项目 | 说明 |
|------|------|
| pytest | Python 测试框架事实标准，插件生态成熟 |
| httpx | 同步/异步均支持，API 与 requests 高度兼容，内置连接池 |
| pydantic v2 | 高性能数据验证，天然适合 L2 结构层断言 |

**优点：**
- httpx 原生支持 `httpx.Client` 用于同步测试、`httpx.AsyncClient` 用于异步测试，无需额外依赖
- pydantic v2（Rust 核心）验证速度比 jsonschema 快 5-50x
- pytest fixtures 体系（`conftest.py`）与 httpx 客户端完美结合
- 类型注解支持完整，与 pyright 配合无缝
- 社区活跃，`pytest-httpx` 可用于 mock 测试

**缺点：**
- pydantic 模型需要手动定义（autoflow 会自动生成，但仍有维护成本）
- httpx 相对 requests 知名度略低，部分老项目文档仍用 requests

**适用场景：** 新项目、需要 async 支持、团队使用现代 Python

```toml
# pyproject.toml 依赖片段
[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "pydantic>=2.7",
    "pytest-cov>=5.0",
]
```

---

### 方案 B：pytest + requests + jsonschema

| 项目 | 说明 |
|------|------|
| pytest | 同方案 A |
| requests | 老牌 HTTP 库，文档极为丰富 |
| jsonschema | JSON Schema Draft 7 验证 |

**优点：**
- requests 几乎是 Python HTTP 客户端的行业代名词，团队学习成本最低
- jsonschema 验证语法是通用标准，非 Python 专属，便于跨语言迁移
- `responses` 库提供 requests 的 mock 支持

**缺点：**
- requests 不支持原生 async（需要 `aiohttp` 补充），不适合异步后端测试
- jsonschema 仅验证结构，无法复用 Python 类型，L2 层断言表达力弱于 pydantic
- jsonschema 验证错误信息可读性差，调试体验不佳
- requests 已进入维护模式，新特性停止添加

**适用场景：** 已有大量 requests 代码的老项目迁移、团队以非 Python 为主语言

---

### 方案 C：Tavern（YAML 驱动测试）

| 项目 | 说明 |
|------|------|
| Tavern | 基于 YAML 配置描述 API 测试，集成 pytest |

**优点：**
- 测试用例为纯 YAML，非技术人员（QA、BA）可直接阅读和编辑
- 内置变量替换、阶段复用（anchors），减少重复代码
- 支持 MQTT、WebSocket 等非 HTTP 协议

**缺点：**
- YAML 不是真正的编程语言：复杂逻辑（循环、条件、动态数据）需要回退到 Python，造成混合代码难以维护
- 调试困难：YAML 中的错误堆栈指向框架内部，定位问题比纯 Python 慢
- L4/L5 高层断言几乎无法在 YAML 中表达，需要大量自定义 hook
- autoflow 生成代码为 Python，与 Tavern YAML 范式不兼容

**适用场景：** 简单的接口冒烟测试、非开发人员主导的测试场景；**不推荐**用于 sisyphus-autoflow 生成的完整测试套件

---

## 测试报告

### 方案 A：Allure（推荐）

**优点：**
- 报告美观、交互性强，支持测试历史趋势、失败截图、请求/响应详情
- 与 CI（Jenkins、GitHub Actions、GitLab CI）集成成熟
- 支持测试分类（Feature、Story）、严重级别标注
- `allure-pytest` 插件支持用装饰器直接在代码中添加报告元数据

**缺点：**
- 需要单独安装 Allure CLI（Java 运行时依赖）
- 报告需要启动本地服务器查看（`allure serve`），不是单个 HTML 文件
- 配置比 pytest-html 复杂

```bash
# 安装 Allure CLI（macOS）
brew install allure

# 运行并生成报告
pytest --alluredir=reports/allure-results
allure serve reports/allure-results
```

**适用场景：** 团队协作、需要历史趋势分析、CI 集成展示

---

### 方案 B：pytest-html

**优点：**
- 安装极简（`pip install pytest-html`），生成单个自包含 HTML 文件
- 无外部依赖，离线可查看
- 配置简单，开箱即用

**缺点：**
- 报告功能基础，无历史趋势、无请求详情展开
- 大规模测试（>1000 个用例）时 HTML 文件体积较大，浏览器渲染慢
- 自定义报告内容需要编写 `conftest.py` hook

```bash
pytest --html=reports/report.html --self-contained-html
```

**适用场景：** 本地快速查看、简单项目、无 CI 集成需求

---

## 代码检查

### 方案 A：ruff（推荐）

**优点：**
- Rust 编写，速度比 flake8 快 10-100x
- 单一工具替代 flake8 + isort + pyupgrade + 部分 pylint
- 支持自动修复（`ruff --fix`）
- 配置简单（`pyproject.toml` 中的 `[tool.ruff]`）
- 与 pyright 配合，覆盖代码质量全链路

**缺点：**
- 部分小众 flake8 插件（如特定框架专用规则）尚未移植到 ruff
- 相对较新，部分保守团队可能偏好经过更长时间检验的工具

```toml
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]
```

---

### 方案 B：flake8 + isort

**优点：**
- flake8 插件生态极为丰富（pep8-naming、flake8-bugbear 等）
- 团队内已有 flake8 配置时迁移成本为零
- isort 是 import 排序的行业标准工具

**缺点：**
- 需要两个工具分别配置（`.flake8` + `pyproject.toml`）
- 速度明显慢于 ruff（大型项目差距显著）
- isort 与 black/ruff format 偶有配置冲突
- 已有被 ruff 全面超越的趋势，长期维护存疑

**适用场景：** 已有成熟 flake8 配置的存量项目

---

## 类型检查

### 方案 A：pyright（推荐）

**优点：**
- 微软出品，VS Code / Pylance 背后的引擎，IDE 集成体验最佳
- 对 pydantic v2、FastAPI、httpx 等现代库的类型推断支持极好
- 严格模式（`strict`）可发现潜在运行时错误
- 速度比 mypy 快（增量检查）

**缺点：**
- 默认配置（`basic` 模式）可能漏报某些问题，需要手动调整为 `standard` 或 `strict`
- 部分老旧库（缺少 `py.typed` 标记）可能出现类型信息丢失警告

```json
// pyrightconfig.json
{
  "pythonVersion": "3.12",
  "typeCheckingMode": "standard",
  "reportMissingImports": true,
  "reportMissingTypeStubs": false
}
```

---

### 方案 B：mypy

**优点：**
- Python 官方推荐的类型检查工具，历史最悠久
- `--strict` 模式覆盖范围极广
- 插件体系成熟（`mypy-pydantic`、`sqlmypy` 等）

**缺点：**
- 速度明显慢于 pyright，大型项目需要配置 `dmypy` 守护进程
- 对 pydantic v2、dataclass transform 等现代特性支持滞后
- 错误信息有时晦涩，调试体验不如 pyright
- 配置文件（`mypy.ini` 或 `setup.cfg`）语法相对繁琐

**适用场景：** 已有 mypy 配置的存量项目、追求最严格标准检查

---

## 总结推荐

| 类别 | 推荐方案 | 备选方案 |
|------|---------|---------|
| 测试框架 | pytest | — |
| HTTP 客户端 | httpx | requests |
| 数据验证 | pydantic v2 | jsonschema |
| 测试报告 | Allure | pytest-html |
| 代码检查 | ruff | flake8 + isort |
| 类型检查 | pyright | mypy |

**默认技术栈（`/using-autoflow` 生成的 `pyproject.toml`）：**

```toml
[project]
name = "api-tests"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "httpx>=0.27",
    "pydantic>=2.7",
]

[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "allure-pytest>=2.13",
]
dev = [
    "ruff>=0.5",
    "pyright>=1.1",
]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "--cov=. --cov-report=term-missing"
```
