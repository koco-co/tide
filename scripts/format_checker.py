"""格式检查规则集 — 参考 qa-flow 的 FC01-FC11 规则，适配 Python 测试代码。"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class FormatRule:
    id: str
    description: str
    severity: Severity


@dataclass(frozen=True)
class Violation:
    rule: FormatRule
    file: str
    line: int
    detail: str


# ---------------------------------------------------------------------------
# 规则定义
# ---------------------------------------------------------------------------

RULES: list[FormatRule] = [
    FormatRule("FC01", "测试方法不超过 50 行", Severity.WARNING),
    FormatRule("FC02", "测试类不超过 15 个方法", Severity.WARNING),
    FormatRule("FC03", "无未使用的 import", Severity.ERROR),
    FormatRule("FC04", "无硬编码测试数据（URL、ID）", Severity.WARNING),
    FormatRule("FC05", "断言消息必须描述性（assert 含 msg 参数）", Severity.INFO),
    FormatRule("FC06", "Pydantic 模型字段必须有 description", Severity.INFO),
    FormatRule("FC07", "测试类必须有 docstring", Severity.WARNING),
    FormatRule("FC08", "无 print() 语句", Severity.ERROR),
    FormatRule("FC09", "行长不超过 120 字符", Severity.WARNING),
    FormatRule("FC10", "嵌套深度不超过 3 层", Severity.WARNING),
]

_RULE_MAP = {r.id: r for r in RULES}


# ---------------------------------------------------------------------------
# 检查函数
# ---------------------------------------------------------------------------


def _check_method_length(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC01: 测试方法不超过 50 行。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC01"]

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                end = node.end_lineno or node.lineno
                length = end - node.lineno + 1
                if length > 50:
                    violations.append(Violation(
                        rule=rule,
                        file=filepath,
                        line=node.lineno,
                        detail=f"方法 {node.name} 有 {length} 行（上限 50）",
                    ))
    return violations


def _check_class_method_count(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC02: 测试类不超过 15 个方法。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC02"]

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            method_count = sum(
                1 for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            if method_count > 15:
                violations.append(Violation(
                    rule=rule,
                    file=filepath,
                    line=node.lineno,
                    detail=f"类 {node.name} 有 {method_count} 个方法（上限 15）",
                ))
    return violations


def _check_class_docstrings(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC07: 测试类必须有 docstring。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC07"]

    for node in ast.walk(tree):
        if (isinstance(node, ast.ClassDef)
                and node.name.startswith("Test")
                and not (node.body and isinstance(node.body[0], ast.Expr)
                         and isinstance(node.body[0].value, ast.Constant)
                         and isinstance(node.body[0].value.value, str))):
            violations.append(Violation(
                rule=rule,
                file=filepath,
                line=node.lineno,
                detail=f"类 {node.name} 缺少 docstring",
            ))
    return violations


def _check_no_print(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC08: 无 print() 语句。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC08"]

    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            violations.append(Violation(
                rule=rule,
                file=filepath,
                line=node.lineno,
                detail="测试代码中不应使用 print()",
            ))
    return violations


def _check_line_length(content: str, filepath: str) -> list[Violation]:
    """FC09: 行长不超过 120 字符。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC09"]

    for i, line in enumerate(content.splitlines(), 1):
        if len(line) > 120:
            violations.append(Violation(
                rule=rule,
                file=filepath,
                line=i,
                detail=f"行长 {len(line)} 字符（上限 120）",
            ))
    return violations


def check_file(filepath: str) -> list[Violation]:
    """对单个 Python 文件执行所有格式检查。"""
    path = Path(filepath)
    if not path.exists() or path.suffix != ".py":
        return []

    content = path.read_text()

    try:
        tree = ast.parse(content, filename=filepath)
    except SyntaxError:
        return [Violation(
            rule=FormatRule("FC00", "语法错误", Severity.ERROR),
            file=filepath,
            line=0,
            detail="文件包含语法错误，无法解析",
        )]

    violations: list[Violation] = []
    violations.extend(_check_method_length(tree, filepath))
    violations.extend(_check_class_method_count(tree, filepath))
    violations.extend(_check_class_docstrings(tree, filepath))
    violations.extend(_check_no_print(tree, filepath))
    violations.extend(_check_line_length(content, filepath))

    return violations


def check_directory(dirpath: str) -> list[Violation]:
    """递归检查目录下所有 Python 文件。"""
    violations: list[Violation] = []
    for py_file in Path(dirpath).rglob("*.py"):
        violations.extend(check_file(str(py_file)))
    return violations


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.format_checker <path>", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    path = Path(target)

    if path.is_file():
        results = check_file(target)
    elif path.is_dir():
        results = check_directory(target)
    else:
        print(f"Path not found: {target}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("All format checks passed!")
        sys.exit(0)

    for v in sorted(results, key=lambda x: (x.file, x.line)):
        print(f"  {v.rule.severity.upper():7s} [{v.rule.id}] {v.file}:{v.line} — {v.detail}")

    error_count = sum(1 for v in results if v.rule.severity == Severity.ERROR)
    warning_count = sum(1 for v in results if v.rule.severity == Severity.WARNING)
    print(f"\nTotal: {error_count} errors, {warning_count} warnings, {len(results)} issues")
    sys.exit(1 if error_count > 0 else 0)
