#!/usr/bin/env python3
"""校验初始化候选稿，并绑定为可确认的精确 JSON 计划。"""

import argparse
import ast
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, cast

from scan_project import load_scope

SCHEMA_VERSION = "1.0"
MAX_RULE_BYTES = 256 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
FORBIDDEN_KEY_PARTS = {
    "authorization",
    "cookie",
    "credential",
    "password",
    "raw_body",
    "request_body",
    "response_body",
    "secret",
    "source_code",
    "token",
}
ABSOLUTE_PATH = re.compile(
    r"(?:^|[\s`\"'(=])(?:/(?:Applications|Library|System|Users|Volumes|etc|home|mnt|opt|private|root|tmp|usr|var|workspace)(?:/|\b)|\\\\|[A-Za-z]:[\\/]|~[/\\])"
)
SAFE_RUNNERS = {
    ("uv", "run", "--locked", "--no-sync", "python"): "uv.lock",
    ("poetry", "run", "python"): "poetry.lock",
    ("pipenv", "run", "python"): "Pipfile.lock",
    ("pdm", "run", "python"): "pdm.lock",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="把已审查的项目画像与动态规则绑定为带 SHA-256 摘要的初始化计划。"
    )
    parser.add_argument("--project-root", required=False, help="待初始化项目根目录。")
    parser.add_argument("--scan", help="scan_project.py 生成的 JSON。")
    parser.add_argument(
        "--scope-plan", help="scan_project.py 生成且已确认的读取范围计划。"
    )
    parser.add_argument("--confirmed-scope-digest", help="用户已确认的读取范围摘要。")
    parser.add_argument("--profile", help="已审查的 project-profile.json 候选。")
    parser.add_argument("--rules-dir", help="已审查的动态 Markdown 规则目录。")
    parser.add_argument("--project-analysis", help="项目扫描角色返回的严格 JSON。")
    parser.add_argument("--test-analysis", help="测试资产扫描角色返回的严格 JSON。")
    parser.add_argument("--review", help="规则审查角色返回的严格 JSON。")
    parser.add_argument("--review-candidate", help="规则审查角色返回的语义结论 JSON。")
    parser.add_argument("--output", help="初始化计划 JSON 输出路径。")
    parser.add_argument(
        "--project-analysis-output", help="归一化后的项目扫描 JSON 输出路径。"
    )
    parser.add_argument(
        "--test-analysis-output", help="归一化后的测试资产扫描 JSON 输出路径。"
    )
    parser.add_argument(
        "--normalize-analyses",
        action="store_true",
        help="把角色的语义结果归一化为绑定脚本使用的确定结构。",
    )
    parser.add_argument(
        "--inspect-candidates",
        action="store_true",
        help="只校验画像与规则候选并输出供审查绑定的摘要。",
    )
    parser.add_argument(
        "--bind-review",
        action="store_true",
        help="把规则审查语义结论绑定到当前画像与规则摘要。",
    )
    parser.add_argument("--self-test", action="store_true", help="运行隔离自检后退出。")
    return parser


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _require_temp_path(path: Path, label: str) -> Path:
    temp_root = Path(tempfile.gettempdir()).resolve()
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(temp_root)
    except ValueError:
        raise ValueError("{}必须位于系统临时目录".format(label))
    return resolved


def _reject_duplicate_keys(pairs: Sequence[Tuple[str, object]]) -> Dict[str, object]:
    value = {}  # type: Dict[str, object]
    for key, child in pairs:
        if key in value:
            raise ValueError("JSON 包含重复字段：{}".format(key))
        value[key] = child
    return value


def _load_json(path: Path, label: str) -> Dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("{}必须是普通文件".format(label))
    _require_temp_path(path, label)
    value = json.loads(
        _read_regular(path, label, MAX_JSON_BYTES).decode("utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError("{}顶层必须是 JSON 对象".format(label))
    return value


def _read_regular(path: Path, label: str, max_bytes: int) -> bytes:
    descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size > max_bytes
        ):
            raise ValueError("{}必须是大小受限的普通文件".format(label))
        chunks = []  # type: List[bytes]
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > max_bytes:
            raise ValueError("{}超过大小限制".format(label))
        return data
    finally:
        os.close(descriptor)


def _walk_json(value: object, location: str = "$") -> Iterable[Tuple[str, object]]:
    yield location, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_json(child, "{}.{}".format(location, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_json(child, "{}[{}]".format(location, index))


def _validate_profile(profile: Dict[str, object]) -> None:
    if profile.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("项目画像 schema_version 必须为 {}".format(SCHEMA_VERSION))
    if profile.get("project_kind") != "python-pytest":
        raise ValueError("项目画像 project_kind 必须为 python-pytest")
    if "runtime_environment_variables" not in profile:
        raise ValueError("项目画像缺少 runtime_environment_variables")
    if "pytest_runner" not in profile:
        raise ValueError("项目画像缺少 pytest_runner")
    if "http_transport" not in profile:
        raise ValueError("项目画像缺少 http_transport")
    python_profile = profile.get("python")
    if not isinstance(python_profile, dict) or set(python_profile) != {
        "constraint",
        "status",
        "evidence",
    }:
        raise ValueError("项目画像缺少严格 Python 版本画像")
    constraint = python_profile["constraint"]
    versions = (
        [int(item) for item in re.findall(r"3\.(\d+)", constraint)]
        if isinstance(constraint, str)
        else []
    )
    if python_profile["status"] != "confirmed" or not versions or min(versions) < 8:
        raise ValueError("项目画像 Python 版本必须有证据确认且最低不早于 3.8")
    _string_list(python_profile["evidence"], "项目画像 Python 证据", allow_empty=False)
    _string_list(
        profile.get("pytest_evidence"), "项目画像 pytest 证据", allow_empty=False
    )
    _string_list(profile.get("test_directories"), "项目画像测试目录", allow_empty=False)
    _validate_profile_runtime_environment_variables(
        profile["runtime_environment_variables"]
    )
    _validate_pytest_runner(profile["pytest_runner"], "项目画像 pytest_runner")
    _validate_http_transport(profile["http_transport"], "项目画像 http_transport")
    for location, value in _walk_json(profile):
        key = location.rsplit(".", 1)[-1].lower()
        if any(part in key for part in FORBIDDEN_KEY_PARTS):
            raise ValueError("项目画像包含禁止字段：{}".format(location))
        if isinstance(value, str):
            if "\x00" in value or ABSOLUTE_PATH.search(value):
                raise ValueError("项目画像包含绝对路径或非法字符：{}".format(location))


def _validate_root(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_symlink():
        raise ValueError("目标项目根目录不能是符号链接")
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("目标项目根目录不存在")
    return root


def _root_identity(root: Path) -> Dict[str, object]:
    stat_result = root.stat()
    return {
        "resolved_path_sha256": hashlib.sha256(str(root).encode("utf-8")).hexdigest(),
        "device": stat_result.st_dev,
        "inode": stat_result.st_ino,
    }


def _string_list(value: object, label: str, allow_empty: bool = True) -> List[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(
            "{}必须是{}字符串数组".format(label, "非空" if not allow_empty else "")
        )
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("{}只能包含非空字符串".format(label))
    return value


def _validate_runtime_environment_variables(
    value: object,
    label: str,
    include_status: bool,
) -> None:
    if not isinstance(value, list):
        raise ValueError("{}必须是数组".format(label))
    seen_names = set()
    expected = {"name", "role", "required", "sensitive", "evidence"}
    if include_status:
        expected.add("status")
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != expected:
            raise ValueError("{}[{}]字段无效".format(label, index))
        name = item["name"]
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name)
            or name in seen_names
        ):
            raise ValueError("{}[{}].name无效或重复".format(label, index))
        seen_names.add(name)
        if item["role"] not in {"target_url", "credential", "runtime"}:
            raise ValueError("{}[{}].role无效".format(label, index))
        if not isinstance(item["required"], bool) or not isinstance(
            item["sensitive"], bool
        ):
            raise ValueError("{}[{}]必需性或敏感性无效".format(label, index))
        _string_list(
            item["evidence"], "{}[{}].evidence".format(label, index), allow_empty=False
        )
        if include_status and item["status"] != "confirmed":
            raise ValueError("{}[{}].status必须为 confirmed".format(label, index))


def _validate_profile_runtime_environment_variables(value: object) -> None:
    _validate_runtime_environment_variables(
        value,
        "项目画像 runtime_environment_variables",
        include_status=True,
    )


def _validate_pytest_runner(value: object, label: str) -> None:
    if not isinstance(value, dict) or set(value) != {
        "argv_prefix",
        "status",
        "evidence",
    }:
        raise ValueError("{}字段无效".format(label))
    argv_prefix = value["argv_prefix"]
    if not isinstance(argv_prefix, list) or any(
        not isinstance(part, str)
        or not part
        or "\x00" in part
        or "\n" in part
        or "\r" in part
        for part in argv_prefix
    ):
        raise ValueError("{}.argv_prefix必须是安全字符串数组".format(label))
    if value["status"] not in {"confirmed", "unknown"}:
        raise ValueError("{}.status无效".format(label))
    if value["status"] == "confirmed" and not argv_prefix:
        raise ValueError("已确认 {} 必须包含 argv_prefix".format(label))
    if value["status"] == "confirmed" and tuple(argv_prefix) not in SAFE_RUNNERS:
        raise ValueError("已确认 {} 不在安全 runner 白名单中".format(label))
    if value["status"] == "unknown" and (argv_prefix or value["evidence"]):
        raise ValueError("未知 {} 不得携带未确认命令或证据".format(label))
    _string_list(
        value["evidence"],
        "{}.evidence".format(label),
        allow_empty=value["status"] == "unknown",
    )


def _validate_http_transport(value: object, label: str) -> None:
    expected = {
        "target_from_environment",
        "redirects_disabled",
        "status",
        "evidence",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("{}字段无效".format(label))
    if value["status"] not in {"confirmed", "unknown"}:
        raise ValueError("{}.status无效".format(label))
    if not isinstance(value["target_from_environment"], bool) or not isinstance(
        value["redirects_disabled"], bool
    ):
        raise ValueError("{}安全开关必须是布尔值".format(label))
    evidence = _string_list(
        value["evidence"],
        "{}.evidence".format(label),
        allow_empty=value["status"] == "unknown",
    )
    if value["status"] == "confirmed" and (
        value["target_from_environment"] is not True
        or value["redirects_disabled"] is not True
    ):
        raise ValueError("已确认 {} 必须绑定环境目标并关闭自动重定向".format(label))
    if value["status"] == "unknown" and (
        value["target_from_environment"] is not False
        or value["redirects_disabled"] is not False
        or evidence
    ):
        raise ValueError("未知 {} 不得携带未确认安全结论".format(label))


def _project_evidence_path(root: Path, relative_value: str, label: str) -> Path:
    relative = Path(relative_value)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in ("", ".", "..") for part in relative.parts)
    ):
        raise ValueError("{}必须是规范的项目内相对路径".format(label))
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("{}包含符号链接".format(label))
    try:
        info = os.lstat(str(current))
    except OSError:
        raise ValueError("{}指向的证据文件不存在".format(label))
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("{}指向的证据文件不存在".format(label))
    return current


def _read_project_evidence(root: Path, relative_value: str, label: str) -> str:
    current = _project_evidence_path(root, relative_value, label)
    return _read_regular(current, label, MAX_RULE_BYTES).decode(
        "utf-8", errors="replace"
    )


def _verify_profile_evidence(root: Path, profile: Dict[str, object]) -> None:
    python_profile = cast(Dict[str, object], profile["python"])
    constraint = cast(str, python_profile["constraint"])
    python_evidence_text = "\n".join(
        _read_project_evidence(root, relative, "Python 版本证据 {}".format(relative))
        for relative in cast(List[str], python_profile["evidence"])
    )
    if constraint not in python_evidence_text:
        raise ValueError("项目画像 Python 版本约束未在所列证据中逐字出现")
    pytest_references = cast(List[str], profile["pytest_evidence"])
    pytest_evidence_text = "\n".join(
        _read_project_evidence(root, relative, "pytest 证据 {}".format(relative))
        for relative in pytest_references
    )
    if "pytest" not in pytest_evidence_text.lower() and not any(
        Path(relative).name == "conftest.py"
        or Path(relative).name.startswith("test_")
        or Path(relative).name.endswith("_test.py")
        for relative in pytest_references
    ):
        raise ValueError("项目画像 pytest 证据未证明 pytest 配置或使用")

    variables = cast(List[Dict[str, object]], profile["runtime_environment_variables"])
    for index, item in enumerate(variables):
        name = cast(str, item["name"])
        evidence_texts = [
            _read_project_evidence(
                root,
                relative,
                "运行时环境变量证据 {}[{}]".format(relative, index),
            )
            for relative in cast(List[str], item["evidence"])
        ]
        if not any(name in text for text in evidence_texts):
            raise ValueError("运行时环境变量 {} 未在所列证据中出现".format(name))

    runner = cast(Dict[str, object], profile["pytest_runner"])
    if runner["status"] == "confirmed":
        prefix = tuple(cast(List[str], runner["argv_prefix"]))
        lock_name = SAFE_RUNNERS.get(prefix)
        if lock_name is None:
            raise ValueError("pytest runner 不在安全 runner 白名单中")
        evidence = {}
        for relative in cast(List[str], runner["evidence"]):
            label = "pytest runner 证据 {}".format(relative)
            if relative == lock_name:
                _project_evidence_path(root, relative, label)
                evidence[relative] = ""
            else:
                evidence[relative] = _read_project_evidence(root, relative, label)
        configuration_evidence = {
            path: text for path, text in evidence.items() if path != lock_name
        }
        if lock_name not in evidence or not any(
            "pytest" in text.lower() for text in configuration_evidence.values()
        ):
            raise ValueError(
                "pytest runner 必须同时由对应锁文件与独立 pytest 配置证据证明"
            )

    transport = cast(Dict[str, object], profile["http_transport"])
    if transport["status"] == "confirmed":
        transport_text = "\n".join(
            _read_project_evidence(
                root, relative, "HTTP transport 证据 {}".format(relative)
            )
            for relative in cast(List[str], transport["evidence"])
        )
        target_names = [
            cast(str, item["name"])
            for item in variables
            if item["role"] == "target_url"
        ]
        if not target_names or not any(name in transport_text for name in target_names):
            raise ValueError("HTTP transport 证据未证明读取已确认目标地址环境变量")
        if (
            re.search(
                r"(?:follow_redirects|allow_redirects)\s*=\s*False\b",
                transport_text,
            )
            is None
        ):
            raise ValueError("HTTP transport 证据未明确关闭自动重定向")


def _evidence_items(value: object, label: str, fields: Sequence[str]) -> None:
    if not isinstance(value, list):
        raise ValueError("{}必须是数组".format(label))
    expected = set(fields)
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != expected:
            raise ValueError("{}[{}]字段无效".format(label, index))
        for field in fields:
            child = item[field]
            if field == "evidence":
                _string_list(
                    child, "{}[{}].evidence".format(label, index), allow_empty=False
                )
            elif not isinstance(child, str) or not child.strip():
                raise ValueError(
                    "{}[{}].{}必须是非空字符串".format(label, index, field)
                )


def _evidence_catalog(scan: Dict[str, object]) -> Dict[str, set]:
    catalog = {}  # type: Dict[str, set]
    roots = [scan.get("project")] + list(
        cast(List[object], scan.get("extra_sources", []))
    )
    for item in roots:
        if not isinstance(item, dict):
            raise ValueError("扫描结果缺少证据文件清单")
        label = item.get("label")
        files = item.get("file_paths")
        if (
            not isinstance(label, str)
            or not isinstance(files, list)
            or any(not isinstance(path, str) for path in files)
        ):
            raise ValueError("扫描结果证据文件清单无效")
        catalog[label] = set(files)
    return catalog


def _snapshot_catalog(scan: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    catalog = {}  # type: Dict[str, Dict[str, object]]
    roots = [scan.get("project")] + list(
        cast(List[object], scan.get("extra_sources", []))
    )
    for item in roots:
        if not isinstance(item, dict) or not isinstance(item.get("label"), str):
            raise ValueError("扫描结果缺少证据快照")
        label = cast(str, item["label"])
        snapshots = item.get("file_snapshots")
        if not isinstance(snapshots, list):
            raise ValueError("扫描结果缺少证据快照：{}".format(label))
        for snapshot in snapshots:
            if not isinstance(snapshot, dict) or set(snapshot) != {
                "path",
                "size",
                "device",
                "inode",
                "sha256",
            }:
                raise ValueError("扫描结果证据快照无效：{}".format(label))
            path = snapshot.get("path")
            digest = snapshot.get("sha256")
            if (
                not isinstance(path, str)
                or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not all(
                    isinstance(snapshot.get(field), int)
                    for field in ("size", "device", "inode")
                )
            ):
                raise ValueError("扫描结果证据快照字段无效：{}".format(label))
            reference = (
                path if label == "current-project" else "{}:{}".format(label, path)
            )
            if reference in catalog:
                raise ValueError("扫描结果证据快照重复：{}".format(reference))
            entry = dict(snapshot, source=label)
            entry["path"] = reference
            catalog[reference] = entry
    return catalog


def _evidence_references(value: object) -> List[str]:
    references = []  # type: List[str]
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "evidence" or key.endswith("_evidence"):
                if isinstance(child, list):
                    references.extend(item for item in child if isinstance(item, str))
            else:
                references.extend(_evidence_references(child))
    elif isinstance(value, list):
        for child in value:
            references.extend(_evidence_references(child))
    return references


def _current_snapshot(
    source_root: Path, reference: str, relative: Optional[str] = None
) -> Dict[str, object]:
    relative_value = reference if relative is None else relative
    path = _project_evidence_path(
        source_root, relative_value, "证据 {}".format(reference)
    )
    descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        return {
            "path": reference,
            "size": info.st_size,
            "device": info.st_dev,
            "inode": info.st_ino,
            "sha256": digest.hexdigest(),
            "source": "current-project"
            if relative is None
            else reference.split(":", 1)[0],
        }
    finally:
        os.close(descriptor)


def _bind_evidence_snapshots(
    root: Path,
    scan: Dict[str, object],
    values: Sequence[object],
    rules: List[Dict[str, object]],
    source_roots: Optional[Dict[str, Path]] = None,
) -> List[Dict[str, object]]:
    scanned = _snapshot_catalog(scan)
    roots = {"current-project": root} if source_roots is None else source_roots
    references = []  # type: List[str]
    for value in values:
        references.extend(_evidence_references(value))
    for rule in rules:
        references.extend(cast(List[str], rule["evidence"]))
    bound = []  # type: List[Dict[str, object]]
    for reference in sorted(set(references)):
        snapshot = scanned.get(reference)
        if snapshot is None:
            raise ValueError("证据引用缺少扫描快照：{}".format(reference))
        source = cast(str, snapshot["source"])
        source_root = roots.get(source)
        if source_root is None:
            raise ValueError("证据来源缺少已确认读取范围：{}".format(source))
        relative = (
            reference if source == "current-project" else reference.split(":", 1)[1]
        )
        current = _current_snapshot(
            source_root,
            reference,
            None if source == "current-project" else relative,
        )
        if current != snapshot:
            raise ValueError("项目证据在扫描后发生变化：{}".format(reference))
        bound.append(snapshot)
    return bound


def _verify_evidence_reference(reference: str, catalog: Dict[str, set]) -> None:
    label = "current-project"
    relative = reference
    if ":" in reference:
        candidate_label, candidate_relative = reference.split(":", 1)
        if candidate_label in catalog:
            label, relative = candidate_label, candidate_relative
    path = Path(relative)
    if (
        label not in catalog
        or path.is_absolute()
        or not path.parts
        or any(part in ("", ".", "..") for part in path.parts)
        or path.as_posix() not in catalog[label]
    ):
        raise ValueError("证据引用未绑定扫描文件清单：{}".format(reference))


def _known_evidence_references(catalog: Dict[str, set]) -> List[str]:
    references = []  # type: List[str]
    for label, paths in sorted(catalog.items()):
        for path in sorted(paths):
            references.append(
                path if label == "current-project" else "{}:{}".format(label, path)
            )
    return references


def _normalize_evidence_value(
    value: object,
    catalog: Dict[str, set],
    label: str,
    allow_empty: bool,
) -> List[str]:
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        raw_items = cast(List[str], value)
    else:
        raise ValueError("{}必须是证据字符串或字符串数组".format(label))
    if not raw_items:
        if allow_empty:
            return []
        raise ValueError("{}不能为空".format(label))

    known = _known_evidence_references(catalog)
    normalized = []  # type: List[str]
    for raw in raw_items:
        if not raw.strip():
            raise ValueError("{}包含空字符串".format(label))
        try:
            _verify_evidence_reference(raw, catalog)
        except ValueError:
            matches = []  # type: List[Tuple[int, int, str]]
            for reference in known:
                start = raw.find(reference)
                if start >= 0:
                    matches.append((start, -len(reference), reference))
            for _, _, reference in sorted(matches):
                if reference not in normalized:
                    normalized.append(reference)
        else:
            if raw not in normalized:
                normalized.append(raw)
    if not normalized and not allow_empty:
        raise ValueError("{}未引用本轮扫描清单中的文件".format(label))
    return normalized


def _normalize_analysis_evidence(
    value: object, catalog: Dict[str, set], location: str = "$"
) -> object:
    if isinstance(value, dict):
        normalized = {}  # type: Dict[str, object]
        for key, child in value.items():
            child_location = "{}.{}".format(location, key)
            if key == "evidence" or key.endswith("_evidence"):
                normalized[key] = _normalize_evidence_value(
                    child,
                    catalog,
                    child_location,
                    allow_empty=isinstance(child, list) and not child,
                )
            else:
                normalized[key] = _normalize_analysis_evidence(
                    child, catalog, child_location
                )
        return normalized
    if isinstance(value, list):
        return [
            _normalize_analysis_evidence(
                child, catalog, "{}[{}]".format(location, index)
            )
            for index, child in enumerate(value)
        ]
    return value


def normalize_analyses(
    scan: Dict[str, object],
    project_analysis: Dict[str, object],
    test_analysis: Dict[str, object],
) -> Tuple[Dict[str, object], Dict[str, object]]:
    catalog = _evidence_catalog(scan)
    normalized_project = cast(
        Dict[str, object], _normalize_analysis_evidence(project_analysis, catalog)
    )

    test_without_runner = dict(test_analysis)
    test_without_runner.pop("pytest_runner", None)
    expected_test_fields = {
        "schema_version",
        "status",
        "pytest_evidence",
        "runtime_environment_variables",
        "http_transport",
        "stable_conventions",
        "candidates",
        "unknowns",
        "rule_topics",
    }
    if set(test_without_runner) != expected_test_fields:
        raise ValueError("测试资产扫描候选字段无效")
    scanned_project = scan.get("project")
    if not isinstance(scanned_project, dict) or "pytest_runner" not in scanned_project:
        raise ValueError("扫描结果缺少脚本确定的 pytest_runner")
    test_without_runner["pytest_runner"] = scanned_project["pytest_runner"]
    normalized_test = cast(
        Dict[str, object], _normalize_analysis_evidence(test_without_runner, catalog)
    )

    _validate_project_analysis(normalized_project)
    _validate_test_analysis(normalized_test)
    _verify_all_evidence(normalized_project, catalog, "项目扫描结果")
    _verify_all_evidence(normalized_test, catalog, "测试资产扫描结果")
    return normalized_project, normalized_test


def _verify_test_directories(
    root: Path, profile: Dict[str, object], catalog: Dict[str, set]
) -> None:
    project_files = catalog.get("current-project", set())
    for raw in cast(List[str], profile["test_directories"]):
        relative = Path(raw)
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in ("", ".", "..") for part in relative.parts)
        ):
            raise ValueError("测试目录必须是项目内规范相对路径：{}".format(raw))
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("测试目录不能经过符号链接：{}".format(raw))
        prefix = relative.as_posix().rstrip("/") + "/"
        if not current.is_dir() or not any(
            path.startswith(prefix) for path in project_files
        ):
            raise ValueError("测试目录未绑定本轮扫描文件清单：{}".format(raw))


def _verify_all_evidence(
    value: object, catalog: Dict[str, set], location: str = "$"
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "evidence" or key.endswith("_evidence"):
                if not isinstance(child, list):
                    raise ValueError("{} evidence 必须是数组".format(location))
                for reference in child:
                    if not isinstance(reference, str):
                        raise ValueError("{} evidence 包含非字符串".format(location))
                    _verify_evidence_reference(reference, catalog)
            else:
                _verify_all_evidence(child, catalog, "{}.{}".format(location, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _verify_all_evidence(child, catalog, "{}[{}]".format(location, index))


def _validate_safe_json(value: Dict[str, object], label: str) -> None:
    for location, child in _walk_json(value):
        key = location.rsplit(".", 1)[-1].lower()
        if any(part in key for part in FORBIDDEN_KEY_PARTS):
            raise ValueError("{}包含禁止字段：{}".format(label, location))
        if isinstance(child, str) and ("\x00" in child or ABSOLUTE_PATH.search(child)):
            raise ValueError("{}包含绝对路径或非法字符：{}".format(label, location))


def _validate_project_analysis(value: Dict[str, object]) -> None:
    expected = {
        "schema_version",
        "status",
        "confirmed_facts",
        "inferences",
        "unknowns",
        "profile_suggestions",
    }
    if set(value) != expected or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("项目扫描结果字段或版本无效")
    if value.get("status") != "COMPLETE":
        raise ValueError("项目扫描角色尚未完成")
    _evidence_items(value["confirmed_facts"], "confirmed_facts", ("fact", "evidence"))
    _evidence_items(
        value["inferences"], "inferences", ("claim", "evidence", "question")
    )
    _string_list(value["unknowns"], "unknowns")
    _string_list(value["profile_suggestions"], "profile_suggestions")
    _validate_safe_json(value, "项目扫描结果")


def _validate_test_analysis(value: Dict[str, object]) -> None:
    expected = {
        "schema_version",
        "status",
        "pytest_evidence",
        "runtime_environment_variables",
        "pytest_runner",
        "http_transport",
        "stable_conventions",
        "candidates",
        "unknowns",
        "rule_topics",
    }
    if set(value) != expected or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("测试资产扫描结果字段或版本无效")
    if value.get("status") != "COMPLETE":
        raise ValueError("测试资产扫描角色尚未完成")
    _string_list(value["pytest_evidence"], "pytest_evidence", allow_empty=False)
    _validate_runtime_environment_variables(
        value["runtime_environment_variables"],
        "runtime_environment_variables",
        include_status=False,
    )
    _validate_pytest_runner(value["pytest_runner"], "pytest_runner")
    _validate_http_transport(value["http_transport"], "http_transport")
    _evidence_items(
        value["stable_conventions"], "stable_conventions", ("convention", "evidence")
    )
    _evidence_items(value["candidates"], "candidates", ("candidate", "evidence", "gap"))
    _string_list(value["unknowns"], "unknowns")
    _evidence_items(value["rule_topics"], "rule_topics", ("topic", "evidence"))
    _validate_safe_json(value, "测试资产扫描结果")


def _validate_review(value: Dict[str, object]) -> None:
    expected = {
        "schema_version",
        "verdict",
        "reviewed_profile_sha256",
        "reviewed_rules_sha256",
        "blocking_findings",
        "non_blocking_findings",
    }
    if set(value) != expected or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("规则审查结果字段或版本无效")
    blockers = value.get("blocking_findings")
    if value.get("verdict") != "PASS" or not isinstance(blockers, list) or blockers:
        raise ValueError("规则审查尚未通过或仍有阻塞问题")
    _string_list(value["non_blocking_findings"], "non_blocking_findings")
    for field in ("reviewed_profile_sha256", "reviewed_rules_sha256"):
        digest = value.get(field)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("规则审查结果缺少有效候选摘要：{}".format(field))
    _validate_safe_json(value, "规则审查结果")


def _collect_rules(rules_dir: Path) -> List[Dict[str, object]]:
    if rules_dir.is_symlink() or not rules_dir.is_dir():
        raise ValueError("规则候选必须是普通目录")
    _require_temp_path(rules_dir, "规则候选")
    rules = []  # type: List[Dict[str, object]]
    for current, dirs, files in os.walk(
        str(rules_dir), topdown=True, followlinks=False
    ):
        current_path = Path(current)
        if any((current_path / name).is_symlink() for name in dirs):
            raise ValueError("规则候选不能包含符号链接目录")
        dirs[:] = sorted(name for name in dirs if not name.startswith("."))
        for name in sorted(files):
            path = current_path / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("规则候选不能包含符号链接或特殊文件")
            relative = path.relative_to(rules_dir).as_posix()
            if name.startswith(".") or path.suffix.lower() != ".md":
                raise ValueError(
                    "规则候选只允许非隐藏 Markdown 文件：{}".format(relative)
                )
            content = _read_regular(
                path, "规则文件 {}".format(relative), MAX_RULE_BYTES
            ).decode("utf-8")
            if not content.strip():
                raise ValueError("规则文件不能为空：{}".format(relative))
            if "\x00" in content or ABSOLUTE_PATH.search(content):
                raise ValueError("规则文件包含绝对路径或非法字符：{}".format(relative))
            if re.search(r"用户(?:已|明确)?确认", content):
                raise ValueError(
                    "规则文件不得把仓库证据误写为本轮用户确认：{}".format(relative)
                )
            first_line = content.splitlines()[0].strip()
            match = re.fullmatch(r"<!-- tide-evidence: (\[.*\]) -->", first_line)
            if match is None:
                raise ValueError(
                    "规则文件首行缺少 tide-evidence JSON：{}".format(relative)
                )
            try:
                evidence = json.loads(match.group(1))
            except ValueError as exc:
                raise ValueError("规则文件证据清单不是有效 JSON：{}".format(exc))
            _string_list(evidence, "规则文件证据清单", allow_empty=False)
            rules.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    "content": content,
                    "evidence": evidence,
                }
            )
    if not rules:
        raise ValueError("至少需要一个由项目事实动态生成的 Markdown 规则")
    return rules


def _call_name(call: ast.Call) -> Optional[str]:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _root_identifier(value: ast.AST) -> Optional[str]:
    current = value
    while isinstance(current, (ast.Attribute, ast.Subscript)):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def _loaded_names(value: ast.AST) -> set:
    return {
        node.id
        for node in ast.walk(value)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


def _stored_names(value: ast.AST) -> set:
    names = {
        node.id
        for node in ast.walk(value)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    root = _root_identifier(value)
    if root is not None and root not in {"self", "cls"}:
        names.add(root)
    return names


def _access_path(value: ast.AST) -> Optional[Tuple[str, ...]]:
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


def _stored_paths(value: ast.AST) -> set:
    if isinstance(value, (ast.Tuple, ast.List)):
        paths = set()
        for child in value.elts:
            paths.update(_stored_paths(child))
        return paths
    if isinstance(value, (ast.Attribute, ast.Subscript)):
        path = _access_path(value)
        return set() if path is None else {path}
    return set()


def _expression_is_tainted(value: ast.AST, tainted: set, tainted_paths: set) -> bool:
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


def _assignment_flow(node: ast.AST) -> Optional[Tuple[ast.AST, List[ast.AST]]]:
    if isinstance(node, ast.Assign):
        return node.value, list(node.targets)
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        return node.value, [node.target]
    if isinstance(node, ast.NamedExpr):
        return node.value, [node.target]
    return None


def _direct_sensitive_response_use(
    definition: ast.AST,
) -> bool:
    if not isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
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
            and node.attr in {"text", "content", "headers", "cookies"}
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
            and node.args[1].value in {"text", "content", "headers", "cookies"}
        ):
            return True
    return False


def _validate_rule_helper_safety(
    root: Path,
    rules: List[Dict[str, object]],
    source_roots: Optional[Dict[str, Path]] = None,
) -> None:
    """拒绝把会泄漏响应内容的既有 helper 或 fixture 固化为生成规则。"""
    roots = {"current-project": root} if source_roots is None else source_roots
    definitions = []  # type: List[ast.AST]
    references = []  # type: List[Tuple[str, str, str]]
    for rule in rules:
        for reference in cast(List[str], rule["evidence"]):
            source = "current-project"
            relative = reference
            if ":" in reference:
                candidate_source, candidate_relative = reference.split(":", 1)
                if candidate_source in roots:
                    source, relative = candidate_source, candidate_relative
            if relative.endswith(".py"):
                references.append((reference, source, relative))
    for reference, source_name, relative in sorted(set(references)):
        source_root = roots.get(source_name)
        if source_root is None:
            raise ValueError("规则证据来源不在已确认读取范围：{}".format(reference))
        source = _read_project_evidence(
            source_root, relative, "规则证据 {}".format(reference)
        )
        try:
            tree = ast.parse(source, filename=reference)
        except SyntaxError:
            continue
        definitions.extend(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
    unsafe = {
        cast(ast.FunctionDef, definition).name
        for definition in definitions
        if _direct_sensitive_response_use(definition)
    }
    changed = True
    while changed:
        changed = False
        for definition in definitions:
            name = cast(ast.FunctionDef, definition).name
            if name in unsafe:
                continue
            called = {
                _call_name(node)
                for node in ast.walk(definition)
                if isinstance(node, ast.Call)
            }
            if called.intersection(unsafe):
                unsafe.add(name)
                changed = True
    for rule in rules:
        content = cast(str, rule["content"])
        mentioned = sorted(
            name
            for name in unsafe
            if re.search(
                r"(?<![A-Za-z0-9_]){}(?![A-Za-z0-9_])".format(re.escape(name)), content
            )
        )
        if mentioned:
            raise ValueError(
                "规则不得推荐会泄漏响应内容的项目 helper 或 fixture：{}（{}）".format(
                    rule["path"], "、".join(mentioned)
                )
            )


def build_plan(
    root: Path,
    scan: Dict[str, object],
    profile: Dict[str, object],
    rules: List[Dict[str, object]],
    project_analysis: Dict[str, object],
    test_analysis: Dict[str, object],
    review: Dict[str, object],
    source_roots: Optional[Dict[str, Path]] = None,
    scope_digest: str = "",
) -> Dict[str, object]:
    if (
        scan.get("schema_version") != SCHEMA_VERSION
        or scan.get("project_kind") != "python-pytest"
    ):
        raise ValueError("扫描结果不是受支持的 Python 与 pytest 项目")
    scan_digest = scan.get("scan_digest")
    scan_without_digest = dict(scan)
    scan_without_digest.pop("scan_digest", None)
    if not isinstance(scan_digest, str) or scan_digest != _digest(scan_without_digest):
        raise ValueError("扫描结果摘要无效")
    if scan.get("target_root_identity") != _root_identity(root):
        raise ValueError("扫描结果未绑定当前目标项目根目录")
    _validate_profile(profile)
    _verify_profile_evidence(root, profile)
    _validate_project_analysis(project_analysis)
    _validate_test_analysis(test_analysis)
    _validate_review(review)
    catalog = _evidence_catalog(scan)
    _verify_test_directories(root, profile, catalog)
    _verify_all_evidence(profile, catalog, "项目画像")
    _verify_all_evidence(project_analysis, catalog, "项目扫描结果")
    _verify_all_evidence(test_analysis, catalog, "测试资产扫描结果")
    scanned_project = scan.get("project")
    if not isinstance(scanned_project, dict) or "pytest_runner" not in scanned_project:
        raise ValueError("扫描结果缺少脚本确定的 pytest_runner")
    _validate_pytest_runner(scanned_project["pytest_runner"], "扫描结果 pytest_runner")
    if test_analysis["pytest_runner"] != scanned_project["pytest_runner"]:
        raise ValueError("测试资产扫描结果 pytest_runner 未绑定确定性扫描结果")
    for rule in rules:
        for reference in cast(List[str], rule["evidence"]):
            _verify_evidence_reference(reference, catalog)
    _validate_rule_helper_safety(root, rules, source_roots)
    expected_runtime_variables = []
    test_runtime_variables = cast(
        List[Dict[str, object]], test_analysis["runtime_environment_variables"]
    )
    for item in test_runtime_variables:
        bound_item = dict(item)
        bound_item["status"] = "confirmed"
        expected_runtime_variables.append(bound_item)
    if profile["runtime_environment_variables"] != expected_runtime_variables:
        raise ValueError("项目画像运行时环境变量未绑定当前测试资产扫描结果")
    if profile["pytest_runner"] != test_analysis["pytest_runner"]:
        raise ValueError("项目画像 pytest_runner 未绑定当前测试资产扫描结果")
    if profile["http_transport"] != test_analysis["http_transport"]:
        raise ValueError("项目画像 http_transport 未绑定当前测试资产扫描结果")
    candidate_summary = candidate_digests(profile, rules, root, source_roots)
    profile_sha256 = cast(str, candidate_summary["profile_sha256"])
    rules_sha256 = cast(str, candidate_summary["rules_sha256"])
    rule_entries = cast(List[Dict[str, object]], candidate_summary["rule_files"])
    if review["reviewed_profile_sha256"] != profile_sha256:
        raise ValueError("规则审查未绑定当前项目画像候选")
    if review["reviewed_rules_sha256"] != rules_sha256:
        raise ValueError("规则审查未绑定当前规则候选")
    project_analysis_sha256 = hashlib.sha256(_canonical(project_analysis)).hexdigest()
    test_analysis_sha256 = hashlib.sha256(_canonical(test_analysis)).hexdigest()
    review_sha256 = hashlib.sha256(_canonical(review)).hexdigest()
    evidence_snapshots = _bind_evidence_snapshots(
        root,
        scan,
        (profile, project_analysis, test_analysis),
        rules,
        source_roots,
    )
    confirmation_summary = {
        "project_kind": "python-pytest",
        "profile_sha256": profile_sha256,
        "project_analysis_sha256": project_analysis_sha256,
        "test_analysis_sha256": test_analysis_sha256,
        "review_sha256": review_sha256,
        "rule_files": rule_entries,
        "write_targets": [".tide/project-profile.json", ".tide/rules/"],
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "init-tide",
        "target_root_identity": _root_identity(root),
        "scan_digest": scan_digest,
        "scope_digest": scope_digest,
        "profile": profile,
        "profile_sha256": profile_sha256,
        "rules": rules,
        "project_analysis_sha256": project_analysis_sha256,
        "test_analysis_sha256": test_analysis_sha256,
        "review_sha256": review_sha256,
        "evidence_snapshots": evidence_snapshots,
        "confirmation_summary": confirmation_summary,
    }  # type: Dict[str, object]
    payload["plan_digest"] = _digest(payload)
    return payload


def candidate_digests(
    profile: Dict[str, object],
    rules: List[Dict[str, object]],
    root: Optional[Path] = None,
    source_roots: Optional[Dict[str, Path]] = None,
) -> Dict[str, object]:
    _validate_profile(profile)
    if root is not None:
        _validate_rule_helper_safety(root, rules, source_roots)
    rule_entries = [{"path": item["path"], "sha256": item["sha256"]} for item in rules]
    return {
        "profile_sha256": hashlib.sha256(_canonical(profile) + b"\n").hexdigest(),
        "rules_sha256": hashlib.sha256(_canonical(rule_entries)).hexdigest(),
        "rule_files": rule_entries,
    }


def bind_review_candidate(
    profile: Dict[str, object],
    rules: List[Dict[str, object]],
    candidate: Dict[str, object],
    root: Optional[Path] = None,
    source_roots: Optional[Dict[str, Path]] = None,
) -> Dict[str, object]:
    expected = {
        "schema_version",
        "verdict",
        "blocking_findings",
        "non_blocking_findings",
    }
    if set(candidate) != expected or candidate.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("规则审查候选字段或版本无效")
    blockers = candidate.get("blocking_findings")
    if candidate.get("verdict") != "PASS" or not isinstance(blockers, list) or blockers:
        raise ValueError("规则审查候选尚未通过或仍有阻塞问题")
    _string_list(candidate["non_blocking_findings"], "non_blocking_findings")
    _validate_safe_json(candidate, "规则审查候选")
    digests = candidate_digests(profile, rules, root, source_roots)
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": "PASS",
        "reviewed_profile_sha256": digests["profile_sha256"],
        "reviewed_rules_sha256": digests["rules_sha256"],
        "blocking_findings": [],
        "non_blocking_findings": candidate["non_blocking_findings"],
    }


def _write_json(path: Path, value: Dict[str, object]) -> None:
    if path.is_symlink() or path.exists():
        raise ValueError("拒绝覆盖既有计划输出")
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise ValueError("计划输出目录必须是已存在的普通目录")
    _require_temp_path(path.parent, "计划输出目录")
    rendered = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    parent_fd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary_name = ".init-tide-bind-{}".format(secrets.token_hex(12))
    descriptor = None  # type: Optional[int]
    try:
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = None
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(
            temporary_name,
            path.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
        os.unlink(temporary_name, dir_fd=parent_fd)
        temporary_name = ""
        os.fsync(parent_fd)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_name:
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        os.close(parent_fd)


def _confirmed_source_roots(
    root: Path, scope_plan: Optional[str], confirmed_scope_digest: Optional[str]
) -> Dict[str, Path]:
    if not scope_plan or not confirmed_scope_digest:
        raise ValueError("必须提供已确认的读取范围计划及其摘要")
    scoped_root, extra_sources = load_scope(Path(scope_plan), confirmed_scope_digest)
    if scoped_root != root:
        raise ValueError("读取范围计划未绑定当前目标项目")
    source_roots = {"current-project": root}
    source_roots.update(dict(extra_sources))
    return source_roots


def _self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="init-tide-bind-") as temp_dir:
        root = Path(temp_dir)
        rules_dir = root / "candidate-rules"
        rules_dir.mkdir()
        (root / "tests").mkdir()
        (root / "tests" / "test_api.py").write_text(
            "def assert_status(result, expected):\n"
            "    if result.status_code != expected:\n"
            "        raise AssertionError(result.text)\n"
            "\n"
            "def authenticated_client(client):\n"
            "    response = client.post('/login')\n"
            "    assert_status(response, 200)\n"
            "    return client\n"
            "\n"
            "def test_api():\n"
            "    assert True\n",
            encoding="utf-8",
        )
        (root / "README.md").write_text(
            "Python >=3.8；python -m pytest\n", encoding="utf-8"
        )
        (rules_dir / "observed-conventions.md").write_text(
            '<!-- tide-evidence: ["tests/test_api.py"] -->\n# 已确认约定\n',
            encoding="utf-8",
        )
        (rules_dir / "unbound-confirmation.md").write_text(
            '<!-- tide-evidence: ["tests/test_api.py"] -->\n# 规则\n- 用户确认必须执行。\n',
            encoding="utf-8",
        )
        try:
            _collect_rules(rules_dir)
        except ValueError:
            pass
        else:
            raise ValueError("自检未阻断把仓库证据误写为用户确认的规则")
        (rules_dir / "unbound-confirmation.md").unlink()
        (rules_dir / "unsafe-helper.md").write_text(
            '<!-- tide-evidence: ["tests/test_api.py"] -->\n'
            "# 不安全约定\n- 认证测试必须复用 authenticated_client。\n",
            encoding="utf-8",
        )
        try:
            _validate_rule_helper_safety(root, _collect_rules(rules_dir))
        except ValueError as exc:
            assert "会泄漏响应内容" in str(exc)
        else:
            raise AssertionError("会泄漏响应内容的项目 fixture 被固化为动态规则")
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
                raise AssertionError("复杂响应别名未被识别为敏感数据流")
        extra_root = root / "shared-source"
        extra_root.mkdir()
        (extra_root / "helper.py").write_text(
            "def shared_helper(result):\n    raise AssertionError(result.text)\n",
            encoding="utf-8",
        )
        extra_rule_content = (
            '<!-- tide-evidence: ["shared:helper.py"] -->\n'
            "# 共享规则\n- 使用 shared_helper。\n"
        )
        extra_rules = [
            {
                "path": "shared.md",
                "sha256": hashlib.sha256(
                    extra_rule_content.encode("utf-8")
                ).hexdigest(),
                "content": extra_rule_content,
                "evidence": ["shared:helper.py"],
            }
        ]
        try:
            _validate_rule_helper_safety(
                root,
                extra_rules,
                {"current-project": root, "shared": extra_root},
            )
        except ValueError as exc:
            assert "会泄漏响应内容" in str(exc)
        else:
            raise AssertionError("额外源码中的不安全 helper 未被拒绝")
        (extra_root / "helper.py").write_text(
            "def shared_helper(result):\n    return result.status_code\n",
            encoding="utf-8",
        )
        _validate_rule_helper_safety(
            root,
            extra_rules,
            {"current-project": root, "shared": extra_root},
        )
        (rules_dir / "unsafe-helper.md").unlink()
        scan_base = {
            "schema_version": SCHEMA_VERSION,
            "project_kind": "python-pytest",
            "target_root_identity": _root_identity(root.resolve()),
            "project": {
                "label": "current-project",
                "file_paths": ["README.md", "tests/test_api.py"],
                "file_snapshots": [
                    {
                        key: value
                        for key, value in _current_snapshot(root, reference).items()
                        if key != "source"
                    }
                    for reference in ("README.md", "tests/test_api.py")
                ],
                "python_detected": True,
                "pytest_detected": True,
                "pytest_runner": {
                    "argv_prefix": [],
                    "status": "unknown",
                    "evidence": [],
                },
            },
            "extra_sources": [],
        }  # type: Dict[str, object]
        scan = dict(scan_base)
        scan["scan_digest"] = _digest(scan_base)
        profile = {
            "schema_version": SCHEMA_VERSION,
            "project_kind": "python-pytest",
            "python": {
                "constraint": ">=3.8",
                "status": "confirmed",
                "evidence": ["README.md"],
            },
            "pytest_evidence": ["tests/test_api.py"],
            "test_directories": ["tests"],
            "evidence": ["tests/test_api.py"],
            "runtime_environment_variables": [],
            "pytest_runner": {"argv_prefix": [], "status": "unknown", "evidence": []},
            "http_transport": {
                "target_from_environment": False,
                "redirects_disabled": False,
                "status": "unknown",
                "evidence": [],
            },
        }
        project_analysis = {
            "schema_version": SCHEMA_VERSION,
            "status": "COMPLETE",
            "confirmed_facts": [
                {"fact": "现有测试目录", "evidence": ["tests/test_api.py"]}
            ],
            "inferences": [],
            "unknowns": [],
            "profile_suggestions": ["使用现有测试目录"],
        }
        test_analysis = {
            "schema_version": SCHEMA_VERSION,
            "status": "COMPLETE",
            "pytest_evidence": ["tests/test_api.py"],
            "runtime_environment_variables": [],
            "pytest_runner": {"argv_prefix": [], "status": "unknown", "evidence": []},
            "http_transport": {
                "target_from_environment": False,
                "redirects_disabled": False,
                "status": "unknown",
                "evidence": [],
            },
            "stable_conventions": [],
            "candidates": [],
            "unknowns": [],
            "rule_topics": [{"topic": "测试结构", "evidence": ["tests/test_api.py"]}],
        }
        raw_project_analysis = dict(project_analysis)
        raw_project_analysis["confirmed_facts"] = [
            {
                "fact": "现有测试目录",
                "evidence": "tests/test_api.py 展示既有 pytest 测试。",
            }
        ]
        raw_test_analysis = dict(test_analysis)
        raw_test_analysis.pop("pytest_runner")
        normalized_project, normalized_test = normalize_analyses(
            scan, raw_project_analysis, raw_test_analysis
        )
        assert normalized_project == project_analysis
        assert normalized_test == test_analysis
        missing_evidence = dict(raw_project_analysis)
        missing_evidence["confirmed_facts"] = [
            {"fact": "无扫描证据", "evidence": "scan.json"}
        ]
        try:
            normalize_analyses(scan, missing_evidence, raw_test_analysis)
        except ValueError as exc:
            assert "未引用本轮扫描清单" in str(exc)
        else:
            raise AssertionError("没有文件引用的描述性证据未被拒绝")
        _validate_safe_json({"fact": "客户端调用 /api/v1/items 路由"}, "接口路由样本")
        try:
            _validate_safe_json(
                {"fact": "读取 /Users/example/project/file.py"}, "本地路径样本"
            )
        except ValueError:
            pass
        else:
            raise AssertionError("常见本地绝对路径未被拒绝")
        rules = _collect_rules(rules_dir)
        review_candidate = {
            "schema_version": SCHEMA_VERSION,
            "verdict": "PASS",
            "blocking_findings": [],
            "non_blocking_findings": [],
        }
        review = bind_review_candidate(profile, rules, review_candidate, root)
        plan = build_plan(
            root.resolve(),
            scan,
            profile,
            rules,
            project_analysis,
            test_analysis,
            review,
        )
        assert plan["plan_digest"]
        assert plan["rules"][0]["path"] == "observed-conventions.md"  # type: ignore[index]
        missing_runtime_variables = dict(profile)
        missing_runtime_variables.pop("runtime_environment_variables")
        try:
            _validate_profile(missing_runtime_variables)
        except ValueError:
            pass
        else:
            raise AssertionError("缺少运行时环境变量字段的项目画像未被拒绝")
        drifted_profile = dict(profile)
        drifted_profile["pytest_runner"] = {
            "argv_prefix": ["python", "-m", "pytest"],
            "status": "confirmed",
            "evidence": ["README.md"],
        }
        drifted_review = dict(review)
        drifted_review["reviewed_profile_sha256"] = hashlib.sha256(
            (_canonical(drifted_profile) + b"\n")
        ).hexdigest()
        try:
            build_plan(
                root.resolve(),
                scan,
                drifted_profile,
                rules,
                project_analysis,
                test_analysis,
                drifted_review,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("漂移的 pytest runner 未被拒绝")
        forged_profile = dict(profile)
        forged_profile["runtime_environment_variables"] = [
            {
                "name": "API_SECRET",
                "role": "credential",
                "required": True,
                "sensitive": True,
                "status": "confirmed",
                "evidence": ["tests/test_api.py"],
            }
        ]
        forged_analysis = dict(test_analysis)
        forged_analysis["runtime_environment_variables"] = [
            {
                "name": "API_SECRET",
                "role": "credential",
                "required": True,
                "sensitive": True,
                "evidence": ["tests/test_api.py"],
            }
        ]
        forged_review = dict(review)
        forged_review["reviewed_profile_sha256"] = hashlib.sha256(
            (_canonical(forged_profile) + b"\n")
        ).hexdigest()
        try:
            build_plan(
                root.resolve(),
                scan,
                forged_profile,
                rules,
                project_analysis,
                forged_analysis,
                forged_review,
            )
        except ValueError as exc:
            assert "未在所列证据中出现" in str(exc)
        else:
            raise AssertionError("未在证据中出现的环境变量未被拒绝")
    print("bind_init_plan.py 自检通过")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.self_test:
        return _self_test()
    if args.normalize_analyses:
        required = [
            args.scan,
            args.project_analysis,
            args.test_analysis,
            args.project_analysis_output,
            args.test_analysis_output,
        ]
        if any(value is None for value in required):
            print(
                "分析归一化失败：必须提供 --scan、两份分析输入与两份输出",
                file=sys.stderr,
            )
            return 2
        try:
            project_output = Path(args.project_analysis_output)
            test_output = Path(args.test_analysis_output)
            if project_output.exists() or test_output.exists():
                raise ValueError("拒绝覆盖既有归一化输出")
            project_analysis, test_analysis = normalize_analyses(
                _load_json(Path(args.scan), "扫描结果"),
                _load_json(Path(args.project_analysis), "项目扫描候选"),
                _load_json(Path(args.test_analysis), "测试资产扫描候选"),
            )
            _write_json(project_output, project_analysis)
            _write_json(test_output, test_analysis)
            print(
                json.dumps(
                    {
                        "project_analysis_sha256": _digest(project_analysis),
                        "test_analysis_sha256": _digest(test_analysis),
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
            print("分析归一化失败：{}".format(exc), file=sys.stderr)
            return 2
    if args.inspect_candidates:
        if (
            not args.project_root
            or not args.profile
            or not args.rules_dir
            or not args.scope_plan
            or not args.confirmed_scope_digest
        ):
            print(
                "候选检查失败：必须提供项目、画像、规则和已确认读取范围",
                file=sys.stderr,
            )
            return 2
        try:
            root = _validate_root(args.project_root)
            source_roots = _confirmed_source_roots(
                root, args.scope_plan, args.confirmed_scope_digest
            )
            value = candidate_digests(
                _load_json(Path(args.profile), "项目画像"),
                _collect_rules(Path(args.rules_dir)),
                root,
                source_roots,
            )
            print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
            print("候选检查失败：{}".format(exc), file=sys.stderr)
            return 2
    if args.bind_review:
        if (
            not args.project_root
            or not args.profile
            or not args.rules_dir
            or not args.review_candidate
            or not args.output
            or not args.scope_plan
            or not args.confirmed_scope_digest
        ):
            print(
                "审查绑定失败：必须提供项目、画像、规则、审查候选、输出和已确认读取范围",
                file=sys.stderr,
            )
            return 2
        try:
            root = _validate_root(args.project_root)
            source_roots = _confirmed_source_roots(
                root, args.scope_plan, args.confirmed_scope_digest
            )
            review = bind_review_candidate(
                _load_json(Path(args.profile), "项目画像"),
                _collect_rules(Path(args.rules_dir)),
                _load_json(Path(args.review_candidate), "规则审查候选"),
                root,
                source_roots,
            )
            _write_json(Path(args.output), review)
            print(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
            print("审查绑定失败：{}".format(exc), file=sys.stderr)
            return 2
    required = [
        args.project_root,
        args.scan,
        args.scope_plan,
        args.confirmed_scope_digest,
        args.profile,
        args.rules_dir,
        args.project_analysis,
        args.test_analysis,
        args.review,
        args.output,
    ]
    if any(value is None for value in required):
        print("绑定失败：除 --self-test 外，所有参数均为必填", file=sys.stderr)
        return 2
    try:
        root = _validate_root(args.project_root)
        source_roots = _confirmed_source_roots(
            root, args.scope_plan, args.confirmed_scope_digest
        )
        scan = _load_json(Path(args.scan), "扫描结果")
        profile = _load_json(Path(args.profile), "项目画像")
        rules = _collect_rules(Path(args.rules_dir))
        project_analysis = _load_json(Path(args.project_analysis), "项目扫描结果")
        test_analysis = _load_json(Path(args.test_analysis), "测试资产扫描结果")
        review = _load_json(Path(args.review), "规则审查结果")
        plan = build_plan(
            root,
            scan,
            profile,
            rules,
            project_analysis,
            test_analysis,
            review,
            source_roots,
            args.confirmed_scope_digest,
        )
        _write_json(Path(args.output), plan)
        print(
            json.dumps(
                {
                    "confirmation_summary": plan["confirmation_summary"],
                    "plan_digest": plan["plan_digest"],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
        print("绑定失败：{}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
