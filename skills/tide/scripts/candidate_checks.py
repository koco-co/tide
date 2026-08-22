#!/usr/bin/env python3
"""确定性校验 Tide 生成的 pytest 候选代码。"""

import argparse
import ast
import json
import os
import re
import stat
import tempfile
from pathlib import Path


MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_FILES = 256
SAFE_FAILURE_FORMAT_NAMES = {
    "evidence_id",
    "scenario_id",
    "status_code",
    "expected_status",
}
FORBIDDEN_OUTPUT_CALLS = {
    "print",
    "pprint",
    "breakpoint",
    "debug",
    "info",
    "warning",
    "error",
    "exception",
    "critical",
}
SENSITIVE_RESPONSE_ATTRIBUTES = {"text", "content", "headers", "cookies"}
RULE_EVIDENCE_PATTERN = re.compile(r"<!-- tide-evidence: (\[.*\]) -->")


class CandidateCheckError(Exception):
    pass


def _relative_path(value, label):
    path = Path(str(value))
    if (
        path.is_absolute()
        or not path.parts
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise CandidateCheckError("%s必须是规范的项目内相对路径。" % label)
    return path


def _target_python_minor(profile):
    python_info = profile.get("python")
    if not isinstance(python_info, dict) or python_info.get("status") != "confirmed":
        raise CandidateCheckError("项目画像缺少已确认 Python 版本。")
    constraint = python_info.get("constraint")
    if not isinstance(constraint, str):
        raise CandidateCheckError("项目画像 Python 版本约束无效。")
    import re

    matches = [int(value) for value in re.findall(r"3\.(\d+)", constraint)]
    if not matches:
        raise CandidateCheckError("无法从项目画像解析 Python 3 版本。")
    return min(matches)


def _parse_target(content, relative, target_minor):
    try:
        return ast.parse(
            content, filename=relative.as_posix(), feature_version=target_minor
        )
    except (SyntaxError, ValueError) as exc:
        line = getattr(exc, "lineno", None)
        raise CandidateCheckError(
            "测试文件不兼容目标 Python 3.%d：%s:%s"
            % (target_minor, relative, line or "?")
        )


def _validate_annotations(tree, relative, target_minor):
    future_annotations = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )
    annotations = []
    if not future_annotations:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                annotations.extend(
                    arg.annotation
                    for arg in node.args.args
                    if arg.annotation is not None
                )
                annotations.extend(
                    arg.annotation
                    for arg in node.args.kwonlyargs
                    if arg.annotation is not None
                )
                if node.args.vararg and node.args.vararg.annotation is not None:
                    annotations.append(node.args.vararg.annotation)
                if node.args.kwarg and node.args.kwarg.annotation is not None:
                    annotations.append(node.args.kwarg.annotation)
                if node.returns is not None:
                    annotations.append(node.returns)
            elif isinstance(node, ast.AnnAssign):
                annotations.append(node.annotation)
    for annotation in annotations:
        for node in ast.walk(annotation):
            if (
                target_minor < 10
                and isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.BitOr)
            ):
                raise CandidateCheckError(
                    "测试文件使用目标 Python 3.%d 不支持的联合类型注解：%s"
                    % (target_minor, relative)
                )
            if (
                target_minor < 9
                and isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id
                in {"list", "dict", "tuple", "set", "frozenset", "type"}
            ):
                raise CandidateCheckError(
                    "测试文件使用目标 Python 3.%d 不支持的内置泛型注解：%s"
                    % (target_minor, relative)
                )


def _call_name(call):
    function = call.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return None


def _is_safe_failure_message(value, safe_names=None):
    if safe_names is None:
        safe_names = set()
    if isinstance(value, ast.Constant):
        return isinstance(value.value, str) and bool(value.value.strip())
    if isinstance(value, ast.Name):
        return value.id in safe_names
    if not isinstance(value, ast.JoinedStr):
        return False
    for part in value.values:
        if isinstance(part, ast.Constant):
            if not isinstance(part.value, str):
                return False
            continue
        if not isinstance(part, ast.FormattedValue):
            return False
        formatted = part.value
        if isinstance(formatted, ast.Name):
            if (
                formatted.id not in SAFE_FAILURE_FORMAT_NAMES
                and formatted.id not in safe_names
            ):
                return False
        elif (
            isinstance(formatted, ast.Attribute)
            and formatted.attr == "status_code"
            and isinstance(formatted.value, ast.Name)
        ):
            pass
        else:
            return False
        if part.format_spec is not None:
            return False
    return True


def _safe_failure_constant_names(tree):
    assignments = {}
    store_counts = {}
    argument_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.arg):
            argument_names.add(node.arg)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            store_counts[node.id] = store_counts.get(node.id, 0) + 1
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                assignments.setdefault(target.id, []).append(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                assignments.setdefault(node.target.id, []).append(node.value)
    safe = set()
    for name, values in assignments.items():
        if (
            name not in argument_names
            and len(values) == store_counts.get(name)
            and values
            and all(_is_safe_failure_message(value) for value in values)
            and len({ast.dump(value, include_attributes=False) for value in values})
            == 1
        ):
            safe.add(name)
    return safe


def _call_argument(call, positional_index, keyword_name):
    if positional_index < len(call.args):
        return call.args[positional_index]
    matches = [item.value for item in call.keywords if item.arg == keyword_name]
    return matches[0] if len(matches) == 1 else None


def _parent_map(tree):
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def _nearest_loop(node, parents):
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.For, ast.AsyncFor, ast.While)):
            return current
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return None
        current = parents.get(current)
    return None


def _inside_exception_handler(node, parents):
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.ExceptHandler):
            return True
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return False
        current = parents.get(current)
    return False


def _safe_failure_parameter_names(tree, safe_constant_names):
    definitions = {}
    duplicate_definitions = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name in definitions:
            duplicate_definitions.add(node.name)
        definitions[node.name] = node

    calls = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            calls.setdefault(node.func.id, []).append(node)

    safe = set()
    parameter_owners = {}
    for function_name, definition in definitions.items():
        if function_name in duplicate_definitions:
            continue
        function_calls = calls.get(function_name, [])
        if not function_calls:
            continue
        parameters = list(definition.args.posonlyargs) + list(definition.args.args)
        for index, parameter in enumerate(parameters):
            parameter_owners.setdefault(parameter.arg, set()).add(function_name)
            values = [
                _call_argument(call, index, parameter.arg) for call in function_calls
            ]
            if all(
                value is not None
                and _is_safe_failure_message(value, safe_constant_names)
                for value in values
            ):
                safe.add(parameter.arg)
    return {name for name in safe if len(parameter_owners.get(name, set())) == 1}


def _validate_safety(tree, relative):
    parents = _parent_map(tree)
    safe_failure_names = _safe_failure_constant_names(tree)
    safe_failure_names.update(_safe_failure_parameter_names(tree, safe_failure_names))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            raise CandidateCheckError(
                "候选测试不得使用可能泄漏求值内容的原生 assert：%s:%d"
                % (relative, node.lineno)
            )
        if isinstance(node, ast.Raise):
            raise CandidateCheckError(
                "候选测试不得直接抛出异常，应使用固定安全消息失败：%s:%d"
                % (relative, node.lineno)
            )
        if isinstance(node, ast.ExceptHandler):
            if not node.body or all(isinstance(item, ast.Pass) for item in node.body):
                raise CandidateCheckError(
                    "候选测试不得吞掉异常：%s:%d" % (relative, node.lineno)
                )
        if isinstance(node, ast.Constant):
            text = node.value
            if isinstance(text, str) and text.lower().startswith(
                ("http://", "https://")
            ):
                raise CandidateCheckError(
                    "测试文件不得硬编码完整目标地址：%s" % relative
                )
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in FORBIDDEN_OUTPUT_CALLS:
            raise CandidateCheckError(
                "候选测试不得打印或记录可能含敏感值的运行时对象：%s:%d"
                % (relative, node.lineno)
            )
        for keyword in node.keywords:
            if (
                keyword.arg in {"follow_redirects", "allow_redirects"}
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
            ):
                raise CandidateCheckError(
                    "测试文件不得自行允许自动重定向：%s" % relative
                )
        if not (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "pytest"
            and node.func.attr == "fail"
        ):
            continue
        if _inside_exception_handler(node, parents):
            raise CandidateCheckError(
                "pytest.fail 不得位于异常处理块内，以免隐式异常链泄漏运行时值：%s:%d"
                % (relative, node.lineno)
            )
        if not node.args or not _is_safe_failure_message(
            node.args[0], safe_failure_names
        ):
            raise CandidateCheckError(
                "pytest.fail 必须使用固定文本或仅格式化证据编号和状态码：%s:%d"
                % (relative, node.lineno)
            )
        pytrace = [item for item in node.keywords if item.arg == "pytrace"]
        if not (
            len(pytrace) == 1
            and isinstance(pytrace[0].value, ast.Constant)
            and pytrace[0].value.value is False
        ):
            raise CandidateCheckError(
                "pytest.fail 必须显式设置 pytrace=False：%s:%d"
                % (relative, node.lineno)
            )


def _assigned_names(node):
    names = set()
    for child in ast.walk(node):
        target = None
        if isinstance(child, ast.AugAssign):
            target = child.target
        elif isinstance(child, ast.Assign):
            for item in child.targets:
                if isinstance(item, ast.Name):
                    names.add(item.id)
        elif isinstance(child, ast.AnnAssign):
            target = child.target
        if isinstance(target, ast.Name):
            names.add(target.id)
    return names


def _validate_pagination_usage(tree, relative):
    parents = _parent_map(tree)
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr.lower() == "get"
            and _client_receiver(node.func.value)
        ):
            continue
        params = [item.value for item in node.keywords if item.arg == "params"]
        for value in params:
            if not isinstance(value, ast.Dict):
                continue
            fields = {}
            for key_node, value_node in zip(value.keys, value.values):
                key = _literal_value(key_node) if key_node is not None else None
                if key is not None and key[0] == "str":
                    fields[key[1]] = value_node
            if not {"skip", "limit"}.issubset(fields):
                continue
            loop = _nearest_loop(node, parents)
            skip_value = fields["skip"]
            if loop is None or not isinstance(skip_value, ast.Name):
                raise CandidateCheckError(
                    "分页成员关系不得只检查固定首屏，必须在循环中推进 skip：%s:%d"
                    % (relative, node.lineno)
                )
            if skip_value.id not in _assigned_names(loop):
                raise CandidateCheckError(
                    "分页循环必须确定性推进 skip 游标：%s:%d" % (relative, node.lineno)
                )


def _cleanup_guard_names(finalbody):
    if (
        len(finalbody) != 1
        or not isinstance(finalbody[0], ast.If)
        or finalbody[0].orelse
    ):
        raise CandidateCheckError("finally 清理必须是唯一且没有 else 的正向 if 守卫。")
    supported = _positive_guard_names(finalbody[0].test)
    if supported is None:
        raise CandidateCheckError(
            "finally 清理守卫只允许正向名称、is not None 与 and 组合。"
        )
    return supported


def _positive_guard_names(test):
    if isinstance(test, ast.Name):
        return {test.id}
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        names = set()
        for value in test.values:
            child = _positive_guard_names(value)
            if child is None:
                return None
            names.update(child)
        return names
    if (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.IsNot)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value is None
    ):
        return {test.left.id}
    return None


def _target_names(target):
    names = {
        node.id
        for node in ast.walk(target)
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del))
    }
    root = _root_identifier(target)
    if root is not None:
        names.add(root)
    return names


def _target_value_pairs(target, value):
    if (
        isinstance(target, (ast.Tuple, ast.List))
        and isinstance(value, (ast.Tuple, ast.List))
        and len(target.elts) == len(value.elts)
    ):
        pairs = []
        for child_target, child_value in zip(target.elts, value.elts):
            pairs.extend(_target_value_pairs(child_target, child_value))
        return pairs
    return [(target, value)]


def _mutation_pairs(node):
    if isinstance(node, ast.Assign):
        pairs = []
        for target in node.targets:
            pairs.extend(_target_value_pairs(target, node.value))
        return pairs
    if isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and node.value is not None:
        return _target_value_pairs(node.target, node.value)
    return []


def _expression_is_falsey(value, falsey_names):
    if isinstance(value, ast.Constant):
        try:
            return not bool(value.value)
        except (TypeError, ValueError):
            return False
    if isinstance(value, (ast.Tuple, ast.List, ast.Set)) and not value.elts:
        return True
    if isinstance(value, ast.Dict) and not value.keys:
        return True
    return isinstance(value, ast.Name) and value.id in falsey_names


def _falsey_names(tree):
    names = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            for target, value in _mutation_pairs(node):
                if not _expression_is_falsey(value, names):
                    continue
                new_names = _target_names(target) - names
                if new_names:
                    names.update(new_names)
                    changed = True
    return names


def _guard_mutations(statement, names):
    matches = []
    for node in ast.walk(statement):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            targets = [node.target]
        elif isinstance(node, ast.Delete):
            targets = node.targets
        else:
            continue
        if any(_target_names(target).intersection(names) for target in targets):
            matches.append(node)
    return matches


def _definitely_disables_positive_guard(node, guard_names, falsey_names):
    if isinstance(node, ast.Delete):
        return True
    return any(
        _target_names(target).intersection(guard_names)
        and _expression_is_falsey(value, falsey_names)
        for target, value in _mutation_pairs(node)
    )


def _validate_cleanup_marker_lifecycle(tree, relative):
    """清理哨兵只能在删除后的全部验证结束后失效。"""
    falsey_names = _falsey_names(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try) or not node.finalbody:
            continue
        guard_names = _cleanup_guard_names(node.finalbody)
        if not guard_names:
            continue
        seen_assignments = set()
        for previous in ast.walk(tree):
            previous_line = getattr(previous, "lineno", None)
            if previous_line is None or previous_line >= node.lineno:
                continue
            for target, value in _mutation_pairs(previous):
                affected = _target_names(target).intersection(guard_names)
                if affected and not _expression_is_falsey(value, falsey_names):
                    seen_assignments.update(affected)
        for index, statement in enumerate(node.body):
            mutations = _guard_mutations(statement, guard_names)
            if not mutations:
                continue
            direct_assignment = isinstance(statement, (ast.Assign, ast.AnnAssign))
            assigned_names = {
                name
                for mutation in mutations
                for target in (
                    mutation.targets
                    if isinstance(mutation, (ast.Assign, ast.Delete))
                    else [mutation.target]
                )
                for name in _target_names(target)
                if name in guard_names
            }
            is_later_assignment = bool(assigned_names.intersection(seen_assignments))
            is_definite_disable = any(
                _definitely_disables_positive_guard(mutation, guard_names, falsey_names)
                for mutation in mutations
            )
            if (is_later_assignment or is_definite_disable) and (
                index != len(node.body) - 1 or not direct_assignment
            ):
                first = mutations[0]
                raise CandidateCheckError(
                    "清理标记只能在删除后的全部验证完成后作为 try 的最后一条语句清除：%s:%d"
                    % (relative, first.lineno)
                )
            seen_assignments.update(assigned_names)


def _client_receiver(value):
    if isinstance(value, ast.Name):
        return "client" in value.id.lower()
    if isinstance(value, ast.Attribute):
        return "client" in value.attr.lower() or _client_receiver(value.value)
    return False


def _literal_value(node):
    if isinstance(node, ast.Constant) and type(node.value) in {
        str,
        int,
        float,
        bool,
        type(None),
    }:
        return (type(node.value).__name__, node.value)
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, (ast.USub, ast.UAdd))
        and isinstance(node.operand, ast.Constant)
        and type(node.operand.value) in {int, float}
    ):
        value = node.operand.value
        if isinstance(node.op, ast.USub):
            value = -value
        return (type(value).__name__, value)
    return None


def _http_parameter_literals(tree):
    found = set()
    methods = {"get", "post", "put", "patch", "delete", "request"}
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr.lower() in methods
            and _client_receiver(node.func.value)
        ):
            continue
        params = [item.value for item in node.keywords if item.arg == "params"]
        for value in params:
            if not isinstance(value, ast.Dict):
                continue
            for key_node, value_node in zip(value.keys, value.values):
                key = _literal_value(key_node) if key_node is not None else None
                child = _literal_value(value_node)
                if key is not None and child is not None:
                    found.add((key, child))
    return found


def _read_evidence_python(root, relative_value):
    if re.match(r"^[a-z][a-z0-9-]{0,31}:", relative_value):
        return None
    relative = _relative_path(relative_value, "项目画像证据路径")
    if relative.suffix != ".py":
        return None
    current = root
    for part in relative.parts:
        current = current / part
        try:
            info = os.lstat(str(current))
        except OSError as exc:
            raise CandidateCheckError("项目画像证据不可用：%s" % exc)
        if stat.S_ISLNK(info.st_mode):
            raise CandidateCheckError("项目画像证据不能经过符号链接：%s" % relative)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_size > MAX_FILE_BYTES
    ):
        raise CandidateCheckError(
            "项目画像 Python 证据必须是大小受限的普通文件：%s" % relative
        )
    descriptor = os.open(str(current), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        opened_info = os.fstat(descriptor)
        if not stat.S_ISREG(opened_info.st_mode) or opened_info.st_nlink != 1:
            raise CandidateCheckError(
                "项目画像 Python 证据必须是唯一普通文件：%s" % relative
            )
        chunks = []
        remaining = MAX_FILE_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
    finally:
        os.close(descriptor)
    if len(data) > MAX_FILE_BYTES:
        raise CandidateCheckError("项目画像 Python 证据超过大小限制：%s" % relative)
    try:
        return data.decode("utf-8")
    except UnicodeError:
        raise CandidateCheckError("项目画像 Python 证据不是 UTF-8：%s" % relative)


def _rule_evidence_references(root):
    rules = root / ".tide" / "rules"
    if rules.is_symlink() or not rules.is_dir():
        return []
    references = []
    for path in sorted(rules.rglob("*")):
        if path.is_symlink():
            raise CandidateCheckError("项目规则不能经过符号链接。")
        try:
            info = os.lstat(str(path))
        except OSError as exc:
            raise CandidateCheckError("无法检查项目规则：%s" % exc)
        if stat.S_ISDIR(info.st_mode):
            continue
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size > MAX_FILE_BYTES
            or path.suffix.lower() != ".md"
        ):
            raise CandidateCheckError("项目规则目录包含非 Markdown 文件。")
        descriptor = None
        try:
            descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
            opened_info = os.fstat(descriptor)
            if not stat.S_ISREG(opened_info.st_mode) or opened_info.st_nlink != 1:
                raise CandidateCheckError("项目规则必须是唯一普通文件：%s" % path.name)
            with os.fdopen(descriptor, "r", encoding="utf-8", closefd=False) as handle:
                first_line = handle.readline(65537).rstrip("\r\n")
        except (OSError, UnicodeError):
            raise CandidateCheckError("项目规则缺少有效证据声明：%s" % path.name)
        finally:
            if descriptor is not None:
                os.close(descriptor)
        if not first_line or len(first_line) > 65536:
            raise CandidateCheckError("项目规则缺少有效证据声明：%s" % path.name)
        match = RULE_EVIDENCE_PATTERN.fullmatch(first_line)
        if match is None:
            raise CandidateCheckError("项目规则证据声明无效：%s" % path.name)
        try:
            declared = json.loads(match.group(1))
        except ValueError:
            raise CandidateCheckError("项目规则证据声明不是有效 JSON：%s" % path.name)
        if not isinstance(declared, list) or any(
            not isinstance(item, str) for item in declared
        ):
            raise CandidateCheckError("项目规则证据声明必须是路径数组：%s" % path.name)
        references.extend(declared)
    return references


def _project_evidence_references(root, profile):
    references = []

    def collect(value, field_name=None):
        if field_name in {"evidence", "pytest_evidence"}:
            if not isinstance(value, list) or any(
                not isinstance(item, str) for item in value
            ):
                raise CandidateCheckError("项目画像包含无效证据字段。")
            references.extend(value)
            return
        if isinstance(value, dict):
            for key, child in value.items():
                collect(child, key)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(profile)
    references.extend(_rule_evidence_references(root))
    unique = []
    for reference in references:
        if reference not in unique:
            unique.append(reference)
    if not unique or len(unique) > MAX_EVIDENCE_FILES:
        raise CandidateCheckError("项目画像与规则缺少有效的项目证据文件清单。")
    return unique


def _root_identifier(value):
    current = value
    while isinstance(current, (ast.Attribute, ast.Subscript)):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
    return None


def _loaded_names(value):
    return {
        node.id
        for node in ast.walk(value)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


def _stored_names(value):
    names = {
        node.id
        for node in ast.walk(value)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    root = _root_identifier(value)
    if root is not None and root not in {"self", "cls"}:
        names.add(root)
    return names


def _access_path(value):
    if isinstance(value, ast.Name):
        return (value.id,)
    if isinstance(value, ast.Attribute):
        parent = _access_path(value.value)
        return None if parent is None else parent + ("." + value.attr,)
    if isinstance(value, ast.Subscript):
        parent = _access_path(value.value)
        if parent is None:
            return None
        return parent + ("[{}]".format(ast.dump(value.slice)),)
    return None


def _stored_paths(value):
    if isinstance(value, (ast.Tuple, ast.List)):
        paths = set()
        for child in value.elts:
            paths.update(_stored_paths(child))
        return paths
    if isinstance(value, (ast.Attribute, ast.Subscript)):
        path = _access_path(value)
        return set() if path is None else {path}
    return set()


def _expression_is_tainted(value, tainted, tainted_paths):
    if _loaded_names(value).intersection(tainted):
        return True
    if isinstance(value, ast.Name) and any(
        path and path[0] == value.id for path in tainted_paths
    ):
        return True
    return any(
        (path := _access_path(node)) is not None and path in tainted_paths
        for node in ast.walk(value)
        if isinstance(node, (ast.Attribute, ast.Subscript))
    )


def _assignment_flow(node):
    if isinstance(node, ast.Assign):
        return node.value, list(node.targets)
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        return node.value, [node.target]
    if isinstance(node, ast.NamedExpr):
        return node.value, [node.target]
    return None


def _direct_sensitive_response_use(definition):
    parameters = {
        item.arg
        for item in (
            list(definition.args.posonlyargs)
            + list(definition.args.args)
            + list(definition.args.kwonlyargs)
        )
        if item.arg not in {"self", "cls"}
    }
    if definition.args.vararg is not None:
        parameters.add(definition.args.vararg.arg)
    if definition.args.kwarg is not None:
        parameters.add(definition.args.kwarg.arg)
    tainted = set(parameters)
    tainted_paths = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(definition):
            flow = _assignment_flow(node)
            if flow is None:
                continue
            value, targets = flow
            if not _expression_is_tainted(value, tainted, tainted_paths):
                continue
            for target in targets:
                new_names = _stored_names(target) - tainted
                new_paths = _stored_paths(target) - tainted_paths
                if new_names:
                    tainted.update(new_names)
                    changed = True
                if new_paths:
                    tainted_paths.update(new_paths)
                    changed = True
        for node in ast.walk(definition):
            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue
            values = list(node.args) + [item.value for item in node.keywords]
            if not any(
                _expression_is_tainted(value, tainted, tainted_paths)
                for value in values
            ):
                continue
            receiver = node.func.value
            new_names = _stored_names(receiver) - tainted
            new_paths = _stored_paths(receiver) - tainted_paths
            if new_names:
                tainted.update(new_names)
                changed = True
            if new_paths:
                tainted_paths.update(new_paths)
                changed = True
    for node in ast.walk(definition):
        if (
            isinstance(node, ast.Attribute)
            and node.attr in SENSITIVE_RESPONSE_ATTRIBUTES
            and (
                _expression_is_tainted(node.value, tainted, tainted_paths)
                or (
                    isinstance(node.value, ast.Name)
                    and node.value.id in {"self", "cls"}
                )
            )
        ):
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "repr"
            and any(
                _expression_is_tainted(item, tainted, tainted_paths)
                for item in node.args
            )
        ):
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and _expression_is_tainted(node.args[0], tainted, tainted_paths)
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value in SENSITIVE_RESPONSE_ATTRIBUTES
        ):
            return True
    return False


def _project_unsafe_symbols(root, profile):
    references = _project_evidence_references(root, profile)
    definitions = []
    for reference in references:
        source = _read_evidence_python(root, reference)
        if source is None:
            continue
        try:
            source_tree = ast.parse(source, filename=reference)
        except SyntaxError:
            continue
        definitions.extend(
            node
            for node in ast.walk(source_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
    unsafe = {
        definition.name
        for definition in definitions
        if _direct_sensitive_response_use(definition)
    }
    changed = True
    while changed:
        changed = False
        for definition in definitions:
            if definition.name in unsafe:
                continue
            called = {
                _call_name(node)
                for node in ast.walk(definition)
                if isinstance(node, ast.Call)
            }
            if called.intersection(unsafe):
                unsafe.add(definition.name)
                changed = True
    return unsafe


def _validate_project_helper_safety(root, profile, tree, relative):
    unsafe = _project_unsafe_symbols(root, profile)
    if not unsafe:
        return
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parameters = (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
            )
            for parameter in parameters:
                if parameter.arg in unsafe:
                    raise CandidateCheckError(
                        "候选测试不得注入会泄漏响应内容的项目 fixture：%s:%d（%s）"
                        % (relative, node.lineno, parameter.arg)
                    )
        if isinstance(node, ast.Call) and _call_name(node) in unsafe:
            raise CandidateCheckError(
                "候选测试不得调用会泄漏响应内容的项目辅助方法：%s:%d（%s）"
                % (relative, node.lineno, _call_name(node))
            )


def _validate_request_parameter_evidence(root, profile, tree, relative):
    references = _project_evidence_references(root, profile)
    supported = set()
    for reference in references:
        source = _read_evidence_python(root, reference)
        if source is None:
            continue
        try:
            source_tree = ast.parse(source, filename=reference)
        except SyntaxError:
            continue
        supported.update(_http_parameter_literals(source_tree))
    unsupported = _http_parameter_literals(tree) - supported
    if unsupported:
        rendered = ", ".join(
            "%r=%r" % (key[1], value[1]) for key, value in sorted(unsupported, key=repr)
        )
        raise CandidateCheckError(
            "候选测试包含项目现有 HTTP 证据未支持的字面量查询参数：%s（%s）"
            % (relative, rendered)
        )


def validate_candidate(root, profile, content, relative_value):
    relative = _relative_path(relative_value, "候选测试路径")
    target_minor = _target_python_minor(profile)
    tree = _parse_target(content, relative, target_minor)
    _validate_annotations(tree, relative, target_minor)
    _validate_safety(tree, relative)
    _validate_project_helper_safety(root, profile, tree, relative)
    _validate_pagination_usage(tree, relative)
    _validate_cleanup_marker_lifecycle(tree, relative)
    _validate_request_parameter_evidence(root, profile, tree, relative)


def _expect_failure(root, profile, content, label):
    try:
        validate_candidate(root, profile, content, "tests/test_candidate.py")
    except CandidateCheckError:
        return
    raise CandidateCheckError("自检未阻断%s。" % label)


def self_test():
    with tempfile.TemporaryDirectory(prefix="tide-candidate-check-test-") as directory:
        root = Path(directory)
        (root / "tests").mkdir()
        (root / ".tide" / "rules").mkdir(parents=True)
        (root / "tests" / "test_api.py").write_text(
            "class ApiClient:\n"
            "    def assert_status(self, result, expected):\n"
            "        if result.status_code != expected:\n"
            "            raise AssertionError(result.text)\n"
            "\n"
            "def authenticated_client(client):\n"
            "    response = client.post('/login')\n"
            "    client.assert_status(response, 200)\n"
            "    return client\n"
            "\n"
            "def test_list(client):\n"
            "    client.get('/items', params={'skip': 0, 'limit': 10})\n",
            encoding="utf-8",
        )
        (root / ".tide" / "rules" / "api.md").write_text(
            '<!-- tide-evidence: ["tests/test_api.py"] -->\n# API 规则\n',
            encoding="utf-8",
        )
        (root / ".tide" / "rules" / "shared.md").write_text(
            '<!-- tide-evidence: ["shared:helper.py"] -->\n# 共享规则\n',
            encoding="utf-8",
        )
        profile = {
            "python": {
                "constraint": ">=3.8",
                "status": "confirmed",
                "evidence": ["tests/test_api.py"],
            },
            "pytest_evidence": ["tests/test_api.py"],
        }
        hardlink = root / "tests" / "hardlink.py"
        os.link(str(root / "tests" / "test_api.py"), str(hardlink))
        try:
            _read_evidence_python(root, "tests/test_api.py")
        except CandidateCheckError:
            pass
        else:
            raise CandidateCheckError("自检未阻断硬链接项目证据。")
        hardlink.unlink()
        validate_candidate(
            root,
            profile,
            "def test_list(client):\n"
            "    offset = 0\n"
            "    while True:\n"
            "        client.get('/items', params={'skip': offset, 'limit': 10})\n"
            "        offset += 10\n"
            "        break\n",
            "tests/test_generated.py",
        )
        validate_candidate(
            root,
            profile,
            "import pytest\n"
            "def test_safe():\n"
            "    failure = 'fixed safe failure'\n"
            "    pytest.fail(failure, pytrace=False)\n",
            "tests/test_safe_failure.py",
        )
        validate_candidate(
            root,
            profile,
            "def test_cleanup():\n"
            "    item_id = None\n"
            "    try:\n"
            "        item_id = 'generated-id'\n"
            "        verify_absent(item_id)\n"
            "        item_id = None\n"
            "    finally:\n"
            "        if item_id is not None:\n"
            "            cleanup(item_id)\n",
            "tests/test_safe_cleanup.py",
        )
        validate_candidate(
            root,
            profile,
            "import pytest\n"
            "def require(condition, message):\n"
            "    if not condition:\n"
            "        pytest.fail(f'check: {message}', pytrace=False)\n"
            "def test_safe():\n"
            "    require(False, 'fixed expectation')\n",
            "tests/test_safe_helper.py",
        )
        _expect_failure(
            root,
            profile,
            "import pytest\n"
            "def require(condition, message):\n"
            "    if not condition:\n"
            "        pytest.fail(f'check: {message}', pytrace=False)\n"
            "def test_bad(response):\n"
            "    require(False, response.text)\n",
            "动态辅助函数失败消息",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad(response):\n    assert response.json()\n",
            "原生 assert",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad(operation):\n"
            "    try:\n"
            "        operation()\n"
            "    except Exception:\n"
            "        pass\n",
            "吞掉异常",
        )
        _expect_failure(
            root,
            profile,
            "import pytest\n"
            "def test_bad(operation):\n"
            "    try:\n"
            "        operation()\n"
            "    except Exception:\n"
            "        pytest.fail('fixed failure', pytrace=False)\n",
            "异常处理块中的隐式异常链",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad(authenticated_client):\n"
            "    authenticated_client.get('/items')\n",
            "会泄漏响应正文的项目 fixture",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad(client, response):\n"
            "    client.assert_status(response, 200)\n",
            "会泄漏响应正文的项目辅助方法",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad(client):\n"
            "    client.get('/items', params={'skip': 0, 'limit': 10})\n",
            "仅检查固定首屏的分页请求",
        )
        _expect_failure(
            root,
            profile,
            "import pytest\n"
            "def test_bad(response):\n"
            "    pytest.fail(f'response={response.text}', pytrace=False)\n",
            "响应值失败消息",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad(response):\n    print(response.text)\n",
            "运行时输出",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad(client):\n"
            "    client.get('/items', params={'skip': 0, 'limit': 100})\n",
            "无证据查询参数",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad_cleanup():\n"
            "    item_id = None\n"
            "    try:\n"
            "        item_id = 'generated-id'\n"
            "        delete(item_id)\n"
            "        item_id = None\n"
            "        verify_absent(item_id)\n"
            "    finally:\n"
            "        if item_id is not None:\n"
            "            cleanup(item_id)\n",
            "过早清除清理标记",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad_cleanup():\n"
            "    cleanup_required = False\n"
            "    try:\n"
            "        cleanup_required = True\n"
            "        delete()\n"
            "        cleanup_required = False\n"
            "        verify_absent()\n"
            "    finally:\n"
            "        if cleanup_required:\n"
            "            cleanup()\n",
            "布尔清理标记过早失效",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad_cleanup():\n"
            "    empty = None\n"
            "    item_id = None\n"
            "    try:\n"
            "        item_id = create()\n"
            "        delete(item_id)\n"
            "        item_id = empty\n"
            "        verify_absent()\n"
            "    finally:\n"
            "        if item_id is not None:\n"
            "            cleanup(item_id)\n",
            "别名清理标记过早失效",
        )
        for reset in (
            "        item_id, ignored = (None, None)\n",
            "        (item_id := None)\n",
            "        del item_id\n",
        ):
            _expect_failure(
                root,
                profile,
                "def test_bad_cleanup():\n"
                "    item_id = None\n"
                "    try:\n"
                "        item_id = create()\n"
                "        delete(item_id)\n" + reset + "        verify_absent()\n"
                "    finally:\n"
                "        if item_id is not None:\n"
                "            cleanup(item_id)\n",
                "解构、海象或删除导致的清理标记提前失效",
            )
        for reset in (
            "        item_id = empty\n",
            "        item_id, ignored = (None, None)\n",
        ):
            _expect_failure(
                root,
                profile,
                "def test_bad_cleanup():\n"
                "    empty = None\n"
                "    item_id = create()\n"
                "    try:\n"
                "        delete(item_id)\n" + reset + "        verify_absent()\n"
                "    finally:\n"
                "        if item_id is not None:\n"
                "            cleanup(item_id)\n",
                "try 外建标记后的别名或解构清理绕过",
            )
        _expect_failure(
            root,
            profile,
            "def test_bad_cleanup():\n"
            "    deleted = False\n"
            "    try:\n"
            "        delete()\n"
            "        deleted = True\n"
            "        verify_absent()\n"
            "    finally:\n"
            "        if not deleted:\n"
            "            cleanup()\n",
            "负向布尔清理守卫",
        )
        _expect_failure(
            root,
            profile,
            "def test_bad_cleanup():\n"
            "    empty = ''\n"
            "    item_id = create()\n"
            "    try:\n"
            "        delete(item_id)\n"
            "        item_id = empty\n"
            "        verify_absent()\n"
            "    finally:\n"
            "        if item_id:\n"
            "            cleanup(item_id)\n",
            "空字符串别名提前关闭清理",
        )
        for finalbody in (
            "        cleanup(item_id) if item_id is not None else None\n",
            "        item_id and cleanup(item_id)\n",
            "        while item_id:\n            cleanup(item_id)\n            break\n",
        ):
            _expect_failure(
                root,
                profile,
                "def test_bad_cleanup():\n"
                "    item_id = create()\n"
                "    try:\n"
                "        delete(item_id)\n"
                "        item_id = None\n"
                "        verify_absent()\n"
                "    finally:\n" + finalbody,
                "非 if 形式的清理守卫",
            )
        for unsafe_source in (
            "def unsafe(result):\n    alias, = (result,)\n    return alias.text\n",
            "def unsafe(result, fallback):\n"
            "    alias = result if result is not None else fallback\n"
            "    return alias.text\n",
            "def unsafe(result):\n    if alias := result:\n        return alias.text\n",
            "def unsafe(result):\n"
            "    box = {}\n"
            "    box['response'] = result\n"
            "    return box['response'].text\n",
            "def unsafe(result):\n"
            "    holder = Box()\n"
            "    holder.response = result\n"
            "    return holder.response.content\n",
            "def unsafe(self):\n    return self.text\n",
            "def unsafe(self, result):\n"
            "    self.payload = result\n"
            "    return self.payload.text\n",
            "def unsafe(cls, result):\n"
            "    cls.items = {}\n"
            "    cls.items['response'] = result\n"
            "    return cls.items['response'].content\n",
            "def unsafe(result):\n    return getattr(result, 'text')\n",
            "def unsafe(result):\n"
            "    box = {}\n"
            "    box.update({'response': result})\n"
            "    return box['response'].text\n",
            "def unsafe(self, result):\n"
            "    alias = self\n"
            "    self.payload = result\n"
            "    return alias.payload.text\n",
        ):
            unsafe_definition = ast.parse(unsafe_source).body[0]
            if not _direct_sensitive_response_use(unsafe_definition):
                raise CandidateCheckError("自检未识别复杂响应别名数据流。")
        _expect_failure(
            root,
            profile,
            "def test_bad(value: list[str]):\n    return None\n",
            "Python 3.8 不兼容注解",
        )


def build_parser():
    parser = argparse.ArgumentParser(description="确定性校验 Tide pytest 候选代码。")
    parser.add_argument("--self-test", action="store_true", help="运行内置自检")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.self_test:
        build_parser().print_help()
        return 0
    try:
        self_test()
    except (CandidateCheckError, OSError) as exc:
        print("错误：%s" % exc, file=os.sys.stderr)
        return 2
    print("candidate_checks.py 自检通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
