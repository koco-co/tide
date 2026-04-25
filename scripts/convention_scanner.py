"""惯例扫描器 — AST 检测目标项目的 API URL 模式、HTTP 客户端、断言风格等规范。

输出 .tide/convention-scout.json 供 project-scanner 生成 convention-fingerprint.yaml。
"""
from __future__ import annotations

import argparse
import ast
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

_EXCLUDED_DIRS = frozenset({".venv", "venv", "__pycache__", "node_modules", "dist", "build"})


def _iter_py_files(root: Path) -> Iterator[Path]:
    """遍历项目中的所有 .py 文件，排除无关目录。"""
    for py_file in root.rglob("*.py"):
        if any(part in _EXCLUDED_DIRS for part in py_file.parts):
            continue
        yield py_file


def _parse_ast(text: str, filename: str) -> ast.Module | None:
    """安全解析 Python 源码为 AST，语法错误返回 None。"""
    try:
        return ast.parse(text, filename=filename)
    except SyntaxError:
        return None


def _has_enum_base(node: ast.ClassDef) -> bool:
    """检查类是否继承自 Enum（支持 enum.Enum 和 Enum 两种写法）。"""
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == "Enum":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Enum":
            return True
    return False


def _is_url_constant(node: ast.AST) -> bool:
    """检查 AST 节点是否是字符串常量赋值给全大写变量。"""
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if (isinstance(target, ast.Name)
                    and target.id.isupper()
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)):
                return True
    return False


def detect_api_pattern(project_root: Path) -> dict[str, Any]:
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

    parsed: list[tuple[Path, ast.Module]] = []
    for filepath in api_files:
        text = filepath.read_text()
        tree = _parse_ast(text, filename=str(filepath))
        if tree is not None:
            parsed.append((filepath, tree))

    # 检查 enum 模式
    enum_modules = []
    for filepath, tree in parsed:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and _has_enum_base(node):
                enum_modules.append({
                    "name": filepath.parent.name,
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

    # 检查 dict / constant 模式
    for _, tree in parsed:
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        return {"type": "dict", "modules": []}

    for _, tree in parsed:
        for node in ast.walk(tree):
            if _is_url_constant(node):
                return {"type": "constant", "modules": []}

    return {"type": "inline", "modules": []}


def detect_http_client(project_root: Path) -> dict[str, Any]:
    """检测 HTTP 客户端：requests / httpx / aiohttp / direct + session 或直接调用。"""
    imports_requests = 0
    imports_httpx = 0
    imports_aiohttp = 0
    uses_session = False
    custom_classes: list[str] = []

    for py_file in _iter_py_files(project_root):
        try:
            text = py_file.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        tree = _parse_ast(text, filename=str(py_file))
        if tree is None:
            continue

        # AST 检测 import
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "requests":
                        imports_requests += 1
                    elif alias.name == "httpx":
                        imports_httpx += 1
                    elif alias.name == "aiohttp":
                        imports_aiohttp += 1
            elif isinstance(node, ast.ImportFrom):
                if node.module == "requests":
                    imports_requests += 1
                elif node.module == "httpx":
                    imports_httpx += 1
                elif node.module == "aiohttp":
                    imports_aiohttp += 1

        # AST 检测 requests.Session()
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "Session"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "requests"):
                uses_session = True
                break

        # AST 检测自定义包装类（包含 post/get/put/delete 的 request/client 类）
        _http_methods = frozenset({"post", "get", "put", "delete", "patch", "options", "head"})
        for node in ast.walk(tree):
            if (isinstance(node, ast.ClassDef)
                    and ("request" in node.name.lower() or "client" in node.name.lower())):
                for item in ast.walk(node):
                    if (isinstance(item, ast.Call)
                            and isinstance(item.func, ast.Attribute)
                            and item.func.attr in _http_methods):
                        custom_classes.append(node.name)
                        break
                    if (isinstance(item, ast.FunctionDef)
                            and item.name in _http_methods):
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

    pattern: str = "custom_class" if custom_classes else ("session" if uses_session else "direct")

    return {
        "library": lib,
        "client_pattern": pattern,
        "custom_class": custom_classes[0] if custom_classes else None,
    }


def detect_assertion_style(test_dir: Path) -> dict[str, Any]:
    """检测断言风格：dict_get / bracket / attr / status_only。

    扫描测试文件中的 assert 语句，统计各类断言的占比。
    """
    counts: dict[str, int] = {"dict_get": 0, "bracket": 0, "attr": 0, "status_only": 0, "total": 0}
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
                if len(samples) < 3 and counts["total"] <= 5 and isinstance(node.test, ast.Compare):
                    samples.append(ast.unparse(node.test))

    if counts["total"] == 0:
        return {"style": "unknown", "common_checks": []}

    dominant = max(counts, key=lambda k: counts[k] if k != "total" else 0)
    return {
        "style": dominant,
        "common_checks": samples,
    }


def detect_allure_pattern(project_root: Path) -> dict[str, Any]:
    """检测 Allure 使用模式。"""
    allure_epic = 0
    allure_title = 0
    allure_step_deco = 0
    allure_step_ctx = 0
    enabled = False

    for py_file in list(project_root.rglob("test_*.py")) + list(project_root.rglob("*_test.py")):
        try:
            text = py_file.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
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
        "step_pattern": (
            "context" if allure_step_ctx > allure_step_deco
            else "decorator" if allure_step_deco > 0
            else "none"
        ),
    }


def detect_service_layer(project_root: Path) -> dict[str, Any]:
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


def detect_auth_method(project_root: Path) -> dict[str, Any]:
    """检测认证方式：cookie / token / basic / none。"""
    auth_keywords: dict[str, int] = {"cookie": 0, "token": 0, "oauth": 0, "basic": 0}

    for py_file in list(project_root.rglob("conftest.py")) + list((project_root / "utils").rglob("*.py")):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            text = py_file.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
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
    dominant = max(auth_keywords, key=lambda k: auth_keywords[k])
    return {"method": dominant}


def detect_test_data_pattern(project_root: Path) -> dict[str, Any]:
    """检测测试数据模式：inline / separated / fixture。"""
    testdata_dir = project_root / "testdata"
    if testdata_dir.is_dir():
        data_files = list(testdata_dir.rglob("*_data.py"))
        test_dir = project_root / "testcases"
        test_files = list(test_dir.rglob("test_*.py")) if test_dir.is_dir() else []
        mirror = False
        if data_files and test_files:
            test_rel = {str(p.relative_to(test_dir)) for p in test_files}
            data_rel = {str(p.relative_to(testdata_dir)).replace("_data.py", "_test.py") for p in data_files}
            mirror = bool(data_rel & test_rel)
        return {
            "pattern": "separated",
            "data_dir": "testdata",
            "mirror_structure": mirror,
        }

    fixtures_dir = project_root / "tests" / "fixtures"
    if fixtures_dir.is_dir() and list(fixtures_dir.rglob("*.py")):
        return {"pattern": "fixture", "data_dir": None, "mirror_structure": False}

    return {"pattern": "inline", "data_dir": None, "mirror_structure": False}


def detect_module_structure(project_root: Path) -> dict[str, Any]:
    """检测项目模块结构：single / multi_module。"""
    modules: list[str] = []
    api_dir = project_root / "api"
    if api_dir.is_dir():
        modules = [d.name for d in api_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
    test_dir = project_root / "testcases" / "scenariotest"
    if test_dir.is_dir():
        test_modules = [d.name for d in test_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
        if test_modules:
            modules = list(set(modules + test_modules))

    return {
        "isolation": "multi_module" if len(modules) > 1 else "single",
        "modules": sorted(modules),
    }


def scan_project(project_root: Path) -> dict[str, Any]:
    """执行所有检测并返回完整的惯例指纹。"""
    test_dir_candidates = [
        project_root / "testcases",
        project_root / "tests",
        project_root / "test",
    ]
    test_dir = next((d for d in test_dir_candidates if d.is_dir()), project_root)

    return {
        "scanned_at": datetime.now(UTC).isoformat(),
        "api": detect_api_pattern(project_root),
        "http_client": detect_http_client(project_root),
        "assertion": detect_assertion_style(test_dir),
        "allure": detect_allure_pattern(project_root),
        "service_layer": detect_service_layer(project_root),
        "auth": detect_auth_method(project_root),
        "test_data": detect_test_data_pattern(project_root),
        "module_structure": detect_module_structure(project_root),
    }


if __name__ == "__main__":
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
