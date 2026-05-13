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
    FormatRule("FC11", "无硬编码业务ID（tableId、dataSourceId等）", Severity.ERROR),
    FormatRule("FC12", "setup_class 必须为实例方法（禁止 @classmethod）", Severity.ERROR),
    FormatRule("FC14", "包含测试方法的类名必须以 Test 开头", Severity.ERROR),
    FormatRule("FC15", "禁止 L4/L5 占位断言或跳过逻辑", Severity.ERROR),
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


def _check_unused_imports(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC03: 无未使用的 import（排除 __future__ 和 typing.TYPE_CHECKING）。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC03"]
    imports: dict[int, str] = {}
    used_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imports[node.lineno] = name
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module == "__future__":
                continue
            for alias in node.names:
                name = alias.asname or alias.name
                imports[node.lineno] = name
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_names.add(node.id)
    for lineno, name in imports.items():
        if name not in used_names:
            violations.append(Violation(rule=rule, file=filepath, line=lineno, detail=f"未使用的 import: {name}"))
    return violations


_CRITICAL_URL_PATTERNS = ("/api/", "/v1/", "/v2/")


def _is_within_enum_class(tree: ast.Module, node: ast.AST) -> bool:
    """检查节点是否在 Enum 类定义内部（API 路径枚举应被豁免）。"""
    for parent in ast.walk(tree):
        if isinstance(parent, ast.ClassDef):
            # 检查类是否继承自 Enum
            is_enum = any(
                isinstance(b, ast.Name) and b.id == "Enum"
                or isinstance(b, ast.Attribute) and b.attr == "Enum"
                for b in parent.bases
            )
            if is_enum:
                for child in ast.walk(parent):
                    if child is node:
                        return True
    return False


def _check_hardcoded_data(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC04: 无硬编码测试数据（URL、长数字 ID）。
    豁免 API Enum 定义中的路径字符串（如 AssetsApi 枚举值）。
    """
    violations: list[Violation] = []
    rule = _RULE_MAP["FC04"]
    for node in ast.walk(tree):
        # Check string constants containing URL patterns (standalone)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str) and any(p in node.value for p in _CRITICAL_URL_PATTERNS):
                # 跳过 Enum 类中的 API 路径定义
                if _is_within_enum_class(tree, node):
                    continue
                violations.append(Violation(rule=rule, file=filepath, line=node.lineno,
                    detail=f"可能的硬编码 URL: {node.value[:60]}"))
            elif isinstance(node.value, int) and node.value > 99999:
                violations.append(Violation(rule=rule, file=filepath, line=node.lineno,
                    detail=f"可能的硬编码 ID: {node.value}"))
    # Also check: self.req.post("/literal/url/..."...) — URL as direct call arg
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            method_name = node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if method_name in ("post", "get", "put", "delete") and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    if any(p in first_arg.value for p in ("/api/", "/v1/", "/v2/")):
                        violations.append(Violation(rule=rule, file=filepath, line=first_arg.lineno,
                            detail=f"直接路径URL（应使用 AssetsApi 枚举）: {first_arg.value[:60]}"))
    return violations


def _check_assert_message(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC05: 断言消息必须描述性（assert 含 msg 参数）。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC05"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert) and node.msg is None:
            violations.append(Violation(rule=rule, file=filepath, line=node.lineno, detail="assert 语句缺少描述消息"))
    return violations


def _check_pydantic_description(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC06: Pydantic 模型字段必须有 description。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC06"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Field":
            has_description = any(kw.arg == "description" for kw in node.keywords)
            if not has_description:
                violations.append(Violation(rule=rule, file=filepath, line=node.lineno, detail="Field() 调用缺少 description 参数"))
    return violations


_NESTED_PARENTS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)


def _check_nesting_depth(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC10: 嵌套深度不超过 3 层。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC10"]
    def _walk(node: ast.AST, depth: int = 0) -> None:
        if depth > 3:
            violations.append(Violation(rule=rule, file=filepath, line=getattr(node, 'lineno', 0), detail=f"嵌套深度超过 3 层（当前 {depth} 层）"))
            return
        for child in ast.iter_child_nodes(node):
            _walk(child, depth + (1 if isinstance(child, _NESTED_PARENTS) else 0))
    _walk(tree)
    return violations


_HARDCODED_ID_KEYS = frozenset({
    "tableId", "dataSourceId", "sourceId", "projectId",
    "tenantId", "catalogueId", "taskId", "userId", "roleId",
    "dsId", "dbId", "clusterId", "engineId", "metaId", "apiId",
})


def _is_business_id_key(key: str) -> bool:
    """Return whether a JSON key represents a runtime business ID."""
    return key in _HARDCODED_ID_KEYS or key.endswith(("Id", "Ids"))


def _literal_business_id(value: ast.AST) -> str | None:
    """Return the hardcoded ID literal if the AST node is a business ID value."""
    if isinstance(value, ast.Constant):
        if isinstance(value.value, int) and value.value != 0:
            return str(value.value)
        if isinstance(value.value, str) and value.value.isdigit() and int(value.value) != 0:
            return value.value
    if isinstance(value, (ast.List, ast.Tuple)):
        for item in value.elts:
            literal = _literal_business_id(item)
            if literal is not None:
                return literal
    return None


def _check_hardcoded_business_ids(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC11: 无硬编码业务ID（tableId、dataSourceId等）。

    检测字典 JSON payload 中数值/数字字符串类型的硬编码业务 ID，要求通过
    运行时查询获取而非写死。
    """
    violations: list[Violation] = []
    rule = _RULE_MAP["FC11"]

    for node in ast.walk(tree):
        # 匹配 {"tableId": 1}、{"dataSourceId": "99999999"} 或 {"roleIds": [1]}。
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                        and _is_business_id_key(key.value)):
                    hardcoded_value = _literal_business_id(value)
                    if hardcoded_value is None:
                        continue
                    violations.append(Violation(
                        rule=rule, file=filepath, line=node.lineno,
                        detail=f"硬编码业务ID: {key.value}={hardcoded_value}，应通过运行时查询获取",
                    ))

    return violations


def _check_classmethod_setup(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC12: setup_class 必须为实例方法（禁止 @classmethod）。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC12"]

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "setup_class":
            # Check for @classmethod decorator
            has_classmethod = any(
                isinstance(d, ast.Name) and d.id == "classmethod"
                or isinstance(d, ast.Attribute) and d.attr == "classmethod"
                for d in node.decorator_list
            )
            if has_classmethod:
                violations.append(Violation(
                    rule=rule, file=filepath, line=node.lineno,
                    detail="setup_class 使用了 @classmethod，必须改为 def setup_class(self) 实例方法模式",
                ))
            # Check for 'cls' as first param name (indicates classmethod-like usage even without decorator)
            args = node.args
            if args.args and args.args[0].arg == "cls" and not has_classmethod:
                violations.append(Violation(
                    rule=rule, file=filepath, line=node.lineno,
                    detail="setup_class 第一个参数为 cls（类方法风格），应使用 self",
                ))
    return violations


def _check_placeholder_l4_l5_assertions(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC15: L4/L5 must not be represented by placeholder pass/skip logic."""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC15"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            message = ""
            if isinstance(node.msg, ast.Constant) and isinstance(node.msg.value, str):
                message = node.msg.value
            is_assert_true = isinstance(node.test, ast.Constant) and node.test.value is True
            if is_assert_true and (
                "requires project-specific wiring" in message
                or message.startswith(("L4 ", "L5 "))
            ):
                violations.append(Violation(
                    rule=rule,
                    file=filepath,
                    line=node.lineno,
                    detail="L4/L5 使用 assert True 占位，未提供可执行断言",
                ))
        elif isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Attribute) and node.func.attr == "skip"):
                continue
            for arg in node.args:
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and "TIDE_ENABLE_" in arg.value
                    and "ASSERTIONS" in arg.value
                ):
                    violations.append(Violation(
                        rule=rule,
                        file=filepath,
                        line=node.lineno,
                        detail="L4/L5 使用环境变量跳过逻辑，未提供默认可执行断言",
                    ))

    return violations


def _check_collectable_test_class_names(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC14: 包含 test_* 方法的类名必须以 Test 开头，确保 pytest 会收集。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC14"]

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name.startswith("Test"):
            continue
        has_test_method = any(
            isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name.startswith("test_")
            for item in node.body
        )
        if has_test_method:
            violations.append(Violation(
                rule=rule,
                file=filepath,
                line=node.lineno,
                detail=f"类 {node.name} 包含 test_* 方法但类名不以 Test 开头，pytest 不会收集",
            ))
    return violations


def _check_scenario_id_uniqueness(files: list[str]) -> list[Violation]:
    """FC13 (跨文件): scenario_id 在生成文件间必须唯一。
    在 check_directory 中调用，接收完整文件列表。
    """
    import re
    rule = FormatRule("FC13", "scenario_id 跨文件唯一性", Severity.ERROR)
    violations: list[Violation] = []
    seen: dict[str, list[str]] = {}

    for filepath in files:
        path = Path(filepath)
        if not path.exists() or path.suffix != ".py":
            continue
        content = path.read_text()
        # Extract scenario_ids from docstrings: """dmetadata_xxx_yyy_zzz"""
        for m in re.finditer(r'"""([a-z]+_[a-z_]+_[a-z]+_[a-z]+)"""', content):
            sid = m.group(1)
            if sid not in seen:
                seen[sid] = []
            seen[sid].append(filepath)

    for sid, locations in seen.items():
        if len(locations) > 1:
            violations.append(Violation(
                rule=rule, file="(cross-file)", line=0,
                detail=f"scenario_id '{sid}' 在 {len(locations)} 个文件中重复: {', '.join(locations)}",
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
    violations.extend(_check_unused_imports(tree, filepath))
    violations.extend(_check_hardcoded_data(tree, filepath))
    violations.extend(_check_assert_message(tree, filepath))
    violations.extend(_check_pydantic_description(tree, filepath))
    violations.extend(_check_nesting_depth(tree, filepath))
    violations.extend(_check_hardcoded_business_ids(tree, filepath))
    violations.extend(_check_classmethod_setup(tree, filepath))
    violations.extend(_check_collectable_test_class_names(tree, filepath))
    violations.extend(_check_placeholder_l4_l5_assertions(tree, filepath))

    return violations


def check_directory(dirpath: str) -> list[Violation]:
    """递归检查目录下所有 Python 文件。"""
    violations: list[Violation] = []
    py_files = []
    for py_file in Path(dirpath).rglob("*.py"):
        py_files.append(str(py_file))
        violations.extend(check_file(str(py_file)))
    violations.extend(_check_scenario_id_uniqueness(py_files))
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
