# 通用适配引擎实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 convention_scanner.py + 修改编排流，使 tide 能自动检测目标项目的代码规范并生成匹配代码

**Architecture:** 新增 scripts/convention_scanner.py 提供 AST 层规范检测，输出 convention-scout.json 供 project-scanner 生成 convention-fingerprint.yaml，case-writer 读取 fingerprint 生成匹配规范的代码。

**Tech Stack:** Python 3.12+, ast, pathlib, yaml, pytest

---

## 文件结构

```
新建:
  scripts/convention_scanner.py      — AST 检测脚本（8 个检测函数 + CLI 入口）
  tests/fixtures/                     — 新增测试用 fixture 目录
  tests/fixtures/sample_enum_api.py   — Enum 模式 API 示例（测试用）
  tests/fixtures/sample_inline_project/ — inline 模式示例项目
  tests/test_convention_scanner.py    — 测试文件

修改:
  agents/project-scanner.md           — 增加 fingerprint 生成指令
  prompts/code-style-python.md        — 增加 fingerprint 适配策略
  skills/tide/SKILL.md            — 预检加载 fingerprint
  skills/using-tide/SKILL.md      — 扫描增加 fingerprint 生成步骤
```

---

### Task 1: convention_scanner.py — API 模式 + HTTP 客户端检测

**Files:**
- Create: `scripts/convention_scanner.py`

- [ ] **Step 1: 创建文件基础结构**

```python
"""惯例扫描器 — AST 检测目标项目的 API URL 模式、HTTP 客户端、断言风格等规范。

输出 .tide/convention-scout.json 供 project-scanner 生成 convention-fingerprint.yaml。
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


def detect_api_pattern(project_root: Path) -> dict:
    """检测 API URL 定义模式：enum / dict / constant / inline。

    遍历 api/**/*.py，检查：
    - class XxxApi(Enum): xxx = 'path' → enum
    - APIS = {'xxx': 'path'}          → dict
    - XXX_URL = 'path'                → constant
    - 未检测到上述模式                 → inline
    """
    api_files = sorted(project_root.glob("api/**/*.py"))
    if not api_files:
        return {"type": "inline", "modules": []}

    enum_modules = []
    for filepath in api_files:
        try:
            tree = ast.parse(filepath.read_text(), filename=str(filepath))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "Enum":
                        module_name = filepath.parent.name
                        enum_modules.append({
                            "name": module_name,
                            "class": node.name,
                            "location": str(filepath.relative_to(project_root)),
                        })
                        break

    if enum_modules:
        return {
            "type": "enum",
            "class_pattern": "{Module}Api",
            "value_access": ".value",
            "modules": enum_modules,
        }

    # 检查 dict 模式
    for filepath in api_files:
        try:
            tree = ast.parse(filepath.read_text(), filename=str(filepath))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        return {
                            "type": "dict",
                            "modules": [],
                        }

    return {"type": "inline", "modules": []}


def detect_http_client(project_root: Path) -> dict:
    """检测 HTTP 客户端：requests / httpx / aiohttp / direct + session 或直接调用。"""
    imports_requests = 0
    imports_httpx = 0
    imports_aiohttp = 0
    uses_session = False
    custom_classes = []

    for py_file in project_root.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            text = py_file.read_text(errors="ignore")
        except Exception:
            continue
        if "import requests" in text or "from requests" in text:
            imports_requests += 1
            if "requests.Session()" in text or "session" in text.lower():
                uses_session = True
        if "import httpx" in text or "from httpx" in text:
            imports_httpx += 1
        if "import aiohttp" in text or "from aiohttp" in text:
            imports_aiohttp += 1

        # 检测自定义包装类
        if "class" in text and ("BaseRequests" in text or "base" in text.lower()):
            try:
                tree = ast.parse(text, filename=str(py_file))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and ("request" in node.name.lower() or "client" in node.name.lower()):
                    for item in ast.walk(node):
                        if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute):
                            if item.func.attr in ("post", "get", "put", "delete"):
                                custom_classes.append(node.name)
                                break

    if imports_httpx > imports_requests and imports_httpx > imports_aiohttp:
        lib = "httpx"
    elif imports_aiohttp > imports_requests and imports_aiohttp > imports_httpx:
        lib = "aiohttp"
    elif imports_requests > 0:
        lib = "requests"
    else:
        lib = "unknown"

    pattern = "custom_class" if custom_classes else ("session" if uses_session else "direct")

    return {
        "library": lib,
        "client_pattern": pattern,
        "custom_class": custom_classes[0] if custom_classes else None,
    }
```

- [ ] **Step 2: 写入文件 → 运行验证**

```bash
uv run python3 -c "from scripts.convention_scanner import detect_api_pattern, detect_http_client; from pathlib import Path; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/convention_scanner.py
git commit -m "feat: 新增 convention_scanner 基础结构 — API 模式 + HTTP 客户端检测"
```

---

### Task 2: convention_scanner.py — 断言风格 + Allure + Service 层检测

**Files:**
- Modify: `scripts/convention_scanner.py`

- [ ] **Step 1: 添加检测函数**

在 `detect_http_client` 之后追加：

```python
def detect_assertion_style(test_dir: Path) -> dict:
    """检测断言风格：dict_get / bracket / attr / status_only。

    扫描测试文件中的 assert 语句，统计各类断言的占比。
    """
    counts = {"dict_get": 0, "bracket": 0, "attr": 0, "status_only": 0, "total": 0}
    samples: list[str] = []

    test_files = list(test_dir.rglob("test_*.py")) + list(test_dir.rglob("*_test.py"))
    for py_file in test_files[:30]:  # 最多扫 30 个文件
        try:
            tree = ast.parse(py_file.read_text(), filename=str(py_file))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert) and node.test:
                counts["total"] += 1
                source = ast.unparse(node.test)
                if ".get(" in source:
                    counts["dict_get"] += 1
                elif source.startswith("resp[") or source.startswith("result["):
                    counts["bracket"] += 1
                elif ".status_code" in source:
                    counts["status_only"] += 1
                elif ".get(" not in source and "[" not in source:
                    counts["attr"] += 1
                if len(samples) < 3 and counts["total"] <= 5:
                    if isinstance(node.test, ast.Compare):
                        samples.append(ast.unparse(node.test))

    if counts["total"] == 0:
        return {"style": "unknown", "common_checks": []}

    dominant = max(counts, key=lambda k: counts[k] if k != "total" else 0)  # type: ignore[arg-type]
    return {
        "style": dominant,
        "common_checks": samples,
    }


def detect_allure_pattern(project_root: Path) -> dict:
    """检测 Allure 使用模式。"""
    allure_epic = 0
    allure_title = 0
    allure_step_deco = 0
    allure_step_ctx = 0
    enabled = False

    for py_file in list(project_root.rglob("test_*.py")) + list(project_root.rglob("*_test.py")):
        try:
            text = py_file.read_text(errors="ignore")
        except Exception:
            continue
        if "import allure" in text or "from allure" in text:
            enabled = True
        if "@allure.epic" in text:
            allure_epic += 1
        if "@allure.title" in text:
            allure_title += 1
        if "with allure.step" in text:
            allure_step_ctx += 1
        if "@allure.step" in text:
            allure_step_deco += 1

    if not enabled:
        return {"enabled": False}

    return {
        "enabled": True,
        "epic_level": allure_epic > 0,
        "title_level": "both" if allure_title > 0 else "none",
        "step_pattern": "context" if allure_step_ctx > allure_step_deco else ("decorator" if allure_step_deco > 0 else "none"),
    }


def detect_service_layer(project_root: Path) -> dict:
    """检测是否使用 Service→Request 分层模式。"""
    utils_dir = project_root / "utils"
    if not utils_dir.is_dir():
        return {"detected": False}

    service_dirs = []
    request_dirs = []

    for d in utils_dir.rglob("*"):
        if d.is_dir() and d.name in ("services", "requests"):
            if d.name == "services":
                service_dirs.append(str(d.relative_to(project_root)))
            else:
                request_dirs.append(str(d.relative_to(project_root)))

    return {
        "detected": len(service_dirs) > 0 and len(request_dirs) > 0,
        "pattern": "service_request" if (service_dirs and request_dirs) else "direct",
    }


def detect_auth_method(project_root: Path) -> dict:
    """检测认证方式：cookie / token / basic / none。"""
    # 扫描 conftest.py 和 common 工具中的认证相关代码
    auth_keywords = {"cookie": 0, "token": 0, "oauth": 0, "basic": 0}

    for py_file in list(project_root.rglob("conftest.py")) + list((project_root / "utils").rglob("*.py")):
        try:
            text = py_file.read_text(errors="ignore")
        except Exception:
            continue
        text_lower = text.lower()
        if "cookie" in text_lower and "cooki" in text_lower:
            auth_keywords["cookie"] += 1
        if "token" in text_lower and "bearer" in text_lower:
            auth_keywords["token"] += 1
        if "oauth" in text_lower:
            auth_keywords["oauth"] += 1
        if "basic" in text_lower and "auth" in text_lower:
            auth_keywords["basic"] += 1

    total = sum(auth_keywords.values())
    if total == 0:
        return {"method": "none"}
    dominant = max(auth_keywords, key=lambda k: auth_keywords[k])  # type: ignore[arg-type]
    return {"method": dominant}
```

- [ ] **Step 2: 添加 detect_test_data_pattern 和 detect_module_structure**

```python
def detect_test_data_pattern(project_root: Path) -> dict:
    """检测测试数据模式：inline / separated / fixture。"""
    testdata_dir = project_root / "testdata"
    if testdata_dir.is_dir():
        data_files = list(testdata_dir.rglob("*_data.py"))
        test_files = list((project_root / "testcases").rglob("test_*.py")) if (project_root / "testcases").is_dir() else []
        mirror = False
        if data_files and test_files:
            # 检查是否镜像结构：testdata/ 与 testcases/ 同构
            test_rel = {str(p.relative_to(project_root / "testcases")) for p in test_files}
            data_rel = {str(p.relative_to(testdata_dir)).replace("_data.py", "_test.py") for p in data_files}
            mirror = bool(data_rel & test_rel)
        return {
            "pattern": "separated",
            "data_dir": "testdata",
            "mirror_structure": mirror,
        }

    # 检查 fixture 或 conftest 中是否有数据提供函数
    fixtures_dir = project_root / "tests" / "fixtures"
    if fixtures_dir.is_dir() and list(fixtures_dir.rglob("*.py")):
        return {"pattern": "fixture", "data_dir": None, "mirror_structure": False}

    return {"pattern": "inline", "data_dir": None, "mirror_structure": False}


def detect_module_structure(project_root: Path) -> dict:
    """检测项目模块结构：single / multi_module。"""
    modules = []
    # 检查 api/ 下子目录数量
    api_dir = project_root / "api"
    if api_dir.is_dir():
        modules = [d.name for d in api_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
    # 检查 testcases/scenariotest 下子目录
    test_dir = project_root / "testcases" / "scenariotest"
    if test_dir.is_dir():
        test_modules = [d.name for d in test_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
        if test_modules:
            modules = list(set(modules + test_modules))

    return {
        "isolation": "multi_module" if len(modules) > 1 else "single",
        "modules": sorted(modules),
    }
```

- [ ] **Step 3: 添加 scan_project 主函数 + CLI 入口**

```python
def scan_project(project_root: Path) -> dict:
    """执行所有检测并返回完整的惯例指纹。"""
    from datetime import datetime, timezone

    test_dir_candidates = [
        project_root / "testcases",
        project_root / "tests",
        project_root / "test",
    ]
    test_dir = next((d for d in test_dir_candidates if d.is_dir()), project_root)

    fingerprint = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "api": detect_api_pattern(project_root),
        "http_client": detect_http_client(project_root),
        "assertion": detect_assertion_style(test_dir),
        "allure": detect_allure_pattern(project_root),
        "service_layer": detect_service_layer(project_root),
        "auth": detect_auth_method(project_root),
        "test_data": detect_test_data_pattern(project_root),
        "module_structure": detect_module_structure(project_root),
    }
    return fingerprint


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Tide convention scanner")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", default=".tide/convention-scout.json")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    result = scan_project(root)

    out_path = root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Scout written to {out_path}")
```

- [ ] **Step 4: 运行验证**

```bash
uv run python3 scripts/convention_scanner.py --project-root /Users/poco/Projects/dtstack-httprunner
```

Expected: 成功输出 scout.json，内容包含 dtstack-httprunner 的正确模式

- [ ] **Step 5: 提交**

```bash
git add scripts/convention_scanner.py
git commit -m "feat: convention_scanner 补全 — 断言/Allure/Service层/认证/数据模式/模块结构检测"
```

---

### Task 3: 测试 convention_scanner.py

**Files:**
- Create: `tests/fixtures/sample_enum_api.py`
- Create: `tests/fixtures/sample_inline_project/conftest.py`
- Create: `tests/fixtures/sample_inline_project/test_demo.py`
- Create: `tests/test_convention_scanner.py`

- [ ] **Step 1: 创建 Enum 模式 fixture**

`tests/fixtures/sample_enum_api.py`:

```python
from enum import Enum


class BatchApi(Enum):
    get_task = "/api/rdos/batch/batchTask/getTaskById"
    add_task = "/api/rdos/batch/batchTask/addOrUpdateTask"
    delete_task = "/api/rdos/batch/batchTask/deleteTask"


class AssetsApi(Enum):
    list_assets = "/dassets/v1/assets/list"
```

- [ ] **Step 2: 创建 inline 模式 fixture 项目**

`tests/fixtures/sample_inline_project/conftest.py`:
```python
import pytest
import requests


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Authorization": "Bearer test"})
    return session
```

`tests/fixtures/sample_inline_project/test_demo.py`:
```python
import pytest
import requests


class TestDemo:
    def test_get_users(self, api_client):
        resp = requests.get("http://example.com/api/v1/users")
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    def test_create_user(self, api_client):
        resp = requests.post("http://example.com/api/v1/users", json={"name": "test"})
        assert resp.json().get("id") is not None
```

- [ ] **Step 3: 创建测试文件**

`tests/test_convention_scanner.py`:

```python
"""Tests for convention scanner."""
from pathlib import Path

from scripts.convention_scanner import (
    detect_api_pattern,
    detect_assertion_style,
    detect_http_client,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestDetectApiPattern:
    def test_detects_enum_pattern(self, tmp_path: Path) -> None:
        api_dir = tmp_path / "api" / "batch"
        api_dir.mkdir(parents=True)
        (api_dir / "__init__.py").write_text("")
        (api_dir / "batch_api.py").write_text(
            "from enum import Enum\nclass BatchApi(Enum):\n    get_task = '/path'"
        )
        result = detect_api_pattern(tmp_path)
        assert result["type"] == "enum"
        assert len(result["modules"]) == 1
        assert result["modules"][0]["class"] == "BatchApi"

    def test_detects_inline_when_no_api_dir(self, tmp_path: Path) -> None:
        result = detect_api_pattern(tmp_path)
        assert result["type"] == "inline"

    def test_detects_inline_when_no_enum(self, tmp_path: Path) -> None:
        api_dir = tmp_path / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "endpoints.py").write_text("ENDPOINTS = {'url': '/path'}")
        result = detect_api_pattern(tmp_path)
        assert result["type"] != "enum"  # dict or inline


class TestDetectHttpClient:
    def test_detects_requests(self, tmp_path: Path) -> None:
        (tmp_path / "test_a.py").write_text("import requests\nrequests.get('/url')")
        result = detect_http_client(tmp_path)
        assert result["library"] == "requests"
        assert result["client_pattern"] == "direct"

    def test_detects_session_usage(self, tmp_path: Path) -> None:
        (tmp_path / "test_b.py").write_text(
            "import requests\nsession = requests.Session()\nsession.get('/url')"
        )
        result = detect_http_client(tmp_path)
        assert result["library"] == "requests"
        assert result["client_pattern"] in ("session", "direct")  # session is valid

    def test_detects_custom_class(self, tmp_path: Path) -> None:
        (tmp_path / "base.py").write_text(
            "class BaseRequests:\n    def post(self, url, **kwargs): ..."
        )
        result = detect_http_client(tmp_path)
        assert result["client_pattern"] == "custom_class"
        assert result["custom_class"] is not None


class TestDetectAssertionStyle:
    def test_detects_dict_get(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_x.py"
        test_file.write_text(
            "def test_x():\n"
            "    resp = {'code': 1}\n"
            "    assert resp.get('code') == 1\n"
        )
        result = detect_assertion_style(tmp_path)
        assert result["style"] == "dict_get"

    def test_detects_bracket(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_y.py"
        test_file.write_text(
            "def test_y():\n"
            "    resp = {'code': 0}\n"
            "    assert resp['code'] == 0\n"
        )
        result = detect_assertion_style(tmp_path)
        assert result["style"] == "bracket"

    def test_empty_dir_returns_unknown(self, tmp_path: Path) -> None:
        result = detect_assertion_style(tmp_path)
        assert result["style"] == "unknown"
```

- [ ] **Step 4: 运行测试**

```bash
uv run pytest tests/test_convention_scanner.py -v --no-cov
```

Expected: 所有测试通过。

- [ ] **Step 5: 提交**

```bash
git add tests/
git commit -m "test: convention_scanner 测试 — Enum/inline 模式、HTTP 客户端、断言风格检测"
```

---

### Task 4: 在 dtstack-httprunner 上验证 scanner

**Files:** 非代码任务

- [ ] **Step 1: 运行 scanner 验证 dtstack-httprunner 的检测结果**

```bash
uv run python3 scripts/convention_scanner.py --project-root /Users/poco/Projects/dtstack-httprunner
```

检查输出 `.tide/convention-scout.json` 的关键字段：
- api.type = enum
- api.modules 包含 batch/assets/dataapi/stream/uic/tag 等
- http_client.library = requests
- http_client.client_pattern = custom_class (BaseRequests)
- assertion.style = dict_get
- allure.enabled = true
- service_layer.detected = true
- auth.method = cookie
- test_data.pattern = separated
- module_structure.isolation = multi_module

- [ ] **Step 2: 提交（若有修改）**

```bash
git add -A
git commit -m "test: 在 dtstack-httprunner 上验证 convention_scanner 检测结果"
```

---

### Task 5: 修改 agents/project-scanner.md

**Files:**
- Modify: `agents/project-scanner.md`

- [ ] **Step 1: 在 project-scanner 指令中增加 fingerprint 生成步骤**

在 agent 指令末尾（输出报告之前）追加：

```
## 阶段五：规范指纹生成

读取 `.tide/convention-scout.json`（由 convention_scanner.py 生成）。

- 若 scout 文件存在：基于 scout 中的检测结果，补全 `convention-fingerprint.yaml`
  - 补充 api.modules 中的详细模块信息
  - 验证 scout 的检测结论是否准确
  - 补充 tide-config.yaml 的 code_style 段
- 若 scout 文件不存在：自行分析项目规范，输出 convention-fingerprint.yaml

写入 `.tide/convention-fingerprint.yaml`，格式参见 prompts/code-style-python.md。

同时更新 `tide-config.yaml` 的 `project.code_style` 段，写入 key 字段供下游 Agent 使用。
```

- [ ] **Step 2: 提交**

```bash
git add agents/project-scanner.md
git commit -m "feat: project-scanner 增加 convention-fingerprint.yaml 生成步骤"
```

---

### Task 6: 修改 prompts/code-style-python.md + SKILL 编排

**Files:**
- Modify: `prompts/code-style-python.md`
- Modify: `skills/tide/SKILL.md`
- Modify: `skills/using-tide/SKILL.md`

- [ ] **Step 1: code-style-python.md 增加 fingerprint 适配策略**

在文件末尾追加：

```
## 惯例指纹适配（convention fingerprint）

当项目存在 `.tide/convention-fingerprint.yaml` 时，case-writer 必须遵循以下映射：

| fingerprint 字段 | 生成代码约束 |
|---|---|
| api.pattern.type=enum | URL 必须通过 {class}.{member}.value 引用，不得硬编码 |
| api.pattern.type=inline | URL 可以硬编码为字符串 |
| http_client.custom_class | HTTP 调用使用该类的 post/get 方法 |
| assertion.style=dict_get | 断言使用 `.get('key')` 方式访问响应字段 |
| assertion.style=bracket | 断言使用 `['key']` 方式访问响应字段 |
| allure.enabled=true | 类级 @allure.epic 和方法级 @allure.title 必加 |
| allure.step_pattern=context | 关键步骤使用 `with allure.step("描述"):` 包裹 |
| test_data.pattern=separated | 测试数据从 testdata/ 模块导入 |
| service_layer.detected=true | 生成的测试直接调用 HTTP，不依赖现有 Service 层 |
| auth.method=cookie | 测试使用 cookie 认证（通过 BaseCookies 或 fixture） |

若 fingerprint 不存在，使用 case-writer 的默认通用代码风格。
```

- [ ] **Step 2: 修改 skills/tide/SKILL.md 预检阶段**

在预检步骤中检查 fingerprint 存在性并注入：

在"预检阶段"的"读取配置"步骤之后，"HAR 校验"之前新增：

```
5.5. **惯例指纹加载**
   test -f .tide/convention-fingerprint.yaml && echo "FINGERPRINT_EXISTS" || echo "NO_FINGERPRINT"
   
   若 fingerprint 存在：
   - 读取 .tide/convention-fingerprint.yaml
   - 将 fingerprint 内容注入后续 wave 的 case-writer prompt 的"项目规范"约束段
   - 设置 fingerprint_mode=true
   若不存在：
   - 设置 fingerprint_mode=false，使用通用默认模板
```

- [ ] **Step 3: 修改 skills/using-tide/SKILL.md**

在"深度扫描"步骤（project-scanner 完成后）增加：

```
5. **规范指纹生成（新增）**
   在 project-scanner 完成之后，项目配置写入之前运行：
   uv run python3 ${CLAUDE_SKILL_DIR}/../../scripts/convention_scanner.py --project-root .
   
   将生成的 convention-fingerprint.yaml 纳入配置引用。
```

- [ ] **Step 4: 提交**

```bash
git add prompts/code-style-python.md skills/tide/SKILL.md skills/using-tide/SKILL.md
git commit -m "feat: 编排流接入 convention fingerprint — scanner → SKILL → case-writer"
```

---

### Task 7: 全量回归

- [ ] **Step 1: 运行全量测试**

```bash
uv run pytest tests/ -v --no-cov
```

Expected: 所有测试通过（含新增的 convention_scanner 测试）。

- [ ] **Step 2: 最终提交**

```bash
git add -A
git status
git commit -m "feat: 通用适配引擎 — convention_scanner + fingerprint 编排流接入"
```
