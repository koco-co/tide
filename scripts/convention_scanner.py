"""惯例扫描器 — AST 检测目标项目的 API URL 模式、HTTP 客户端、断言风格等规范。

输出 .autoflow/convention-scout.json 供 project-scanner 生成 convention-fingerprint.yaml。
"""
from __future__ import annotations

import ast
import json
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


def scan_project(project_root: Path) -> dict:
    """执行所有检测并返回完整的惯例指纹。"""
    from datetime import datetime, timezone

    fingerprint = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "api": detect_api_pattern(project_root),
        "http_client": detect_http_client(project_root),
    }
    return fingerprint


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AutoFlow convention scanner")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", default=".autoflow/convention-scout.json")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    result = scan_project(root)

    out_path = root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Scout written to {out_path}")
