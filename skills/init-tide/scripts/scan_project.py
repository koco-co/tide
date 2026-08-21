#!/usr/bin/env python3
"""只读扫描已有 Python 与 pytest 项目的确定性事实。"""

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SCHEMA_VERSION = "1.0"
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tide",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "venv",
}
MAX_FILES = 20000
MAX_TEXT_BYTES = 1024 * 1024
SENSITIVE_FILE_NAMES = {
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ed25519",
    "id_rsa",
    "secrets.json",
}
SENSITIVE_SUFFIXES = {".har", ".key", ".p12", ".pem", ".pfx"}
SAFE_PYTEST_RUNNERS = (
    ("uv.lock", ["uv", "run", "--locked", "--no-sync", "python"]),
    ("poetry.lock", ["poetry", "run", "python"]),
    ("Pipfile.lock", ["pipenv", "run", "python"]),
    ("pdm.lock", ["pdm", "run", "python"]),
)
ROOT_PYTEST_CONFIGS = ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "只读扫描已有 Python 与 pytest 项目，"
            "输出不含绝对路径和文件正文的 JSON 事实清单。"
        )
    )
    parser.add_argument(
        "--project-root", default=".", help="目标项目根目录，默认为当前目录。"
    )
    parser.add_argument(
        "--extra-source",
        action="append",
        default=[],
        metavar="标签=目录",
        help="已逐项授权的额外本地源码目录；可重复使用，输出只保留标签。",
    )
    parser.add_argument(
        "--output", default="-", help="输出 JSON 路径；使用 - 输出到标准输出。"
    )
    parser.add_argument(
        "--prepare-scope", action="store_true", help="生成待读取范围确认计划"
    )
    parser.add_argument("--scope-plan", help="已确认的系统临时范围计划")
    parser.add_argument("--confirmed-scope-digest", help="用户确认的读取范围摘要")
    parser.add_argument("--self-test", action="store_true", help="运行隔离自检后退出。")
    return parser


def _resolve_directory(raw_path: str, label: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_symlink():
        raise ValueError("{}不能是符号链接目录".format(label))
    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError("{}不是可读取目录".format(label))
    if not os.access(str(resolved), os.R_OK | os.X_OK):
        raise ValueError("{}不可读取".format(label))
    return resolved


def _parse_extra(values: Sequence[str]) -> List[Tuple[str, Path]]:
    parsed = []  # type: List[Tuple[str, Path]]
    labels = set()
    for value in values:
        if "=" not in value:
            raise ValueError("额外源码必须使用 标签=目录 格式")
        label, raw_path = value.split("=", 1)
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", label):
            raise ValueError("额外源码标签必须是小写字母开头的短横线名称")
        if label in labels or label == "current-project":
            raise ValueError("额外源码标签重复或保留：{}".format(label))
        labels.add(label)
        parsed.append(
            (label, _resolve_directory(raw_path, "额外源码 {}".format(label)))
        )
    return parsed


def _walk_files(root: Path) -> List[Path]:
    result = []  # type: List[Path]
    for current, dirs, files in os.walk(str(root), topdown=True, followlinks=False):
        current_path = Path(current)
        dirs[:] = sorted(
            name
            for name in dirs
            if name not in IGNORED_DIRS and not (current_path / name).is_symlink()
        )
        for name in sorted(files):
            path = current_path / name
            lowered = name.lower()
            if (
                path.is_symlink()
                or not path.is_file()
                or lowered == ".env"
                or lowered.startswith(".env.")
                or lowered in SENSITIVE_FILE_NAMES
                or path.suffix.lower() in SENSITIVE_SUFFIXES
            ):
                continue
            result.append(path)
            if len(result) > MAX_FILES:
                raise ValueError("扫描文件超过 {} 个，已失败关闭".format(MAX_FILES))
    return result


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_text(path: Path) -> str:
    descriptor = None
    try:
        descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_TEXT_BYTES:
            return ""
        chunks = []  # type: List[bytes]
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")
    except OSError:
        return ""
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _unique(values: Iterable[str]) -> List[str]:
    return sorted(set(values))


def _detect_pytest_runner(
    relative_files: Sequence[Tuple[str, Path]], pytest_evidence: Sequence[str]
) -> Dict[str, object]:
    """只用根目录锁文件与独立 pytest 配置确定安全 runner。"""
    paths = {relative: path for relative, path in relative_files}
    locks = [
        (lock_name, argv_prefix)
        for lock_name, argv_prefix in SAFE_PYTEST_RUNNERS
        if lock_name in paths
    ]
    configs = [
        name
        for name in ROOT_PYTEST_CONFIGS
        if name in paths and name in pytest_evidence
    ]
    if len(locks) != 1 or not configs:
        return {"argv_prefix": [], "status": "unknown", "evidence": []}
    lock_name, argv_prefix = locks[0]
    return {
        "argv_prefix": argv_prefix,
        "status": "confirmed",
        "evidence": [lock_name] + sorted(configs),
    }


def _scan_root(root: Path, label: str) -> Dict[str, object]:
    files = _walk_files(root)
    relative_files = [(_relative(path, root), path) for path in files]
    python_files = [rel for rel, _ in relative_files if rel.endswith(".py")]
    python_evidence = list(python_files[:20])
    for marker in ("pyproject.toml", "setup.cfg", "setup.py", "requirements.txt"):
        if any(rel == marker for rel, _ in relative_files):
            python_evidence.append(marker)

    pytest_evidence = []  # type: List[str]
    python_constraint = None  # type: Optional[str]
    config_names = {
        "pyproject.toml",
        "setup.cfg",
        "tox.ini",
        "pytest.ini",
        "requirements.txt",
    }
    for rel, path in relative_files:
        if rel not in config_names and not rel.endswith(
            (
                "/pyproject.toml",
                "/setup.cfg",
                "/tox.ini",
                "/pytest.ini",
                "/requirements.txt",
            )
        ):
            continue
        text = _read_text(path)
        lowered = text.lower()
        if "pytest" in lowered or "[tool.pytest" in lowered:
            pytest_evidence.append(rel)
        if python_constraint is None:
            match = re.search(
                r"requires-python\s*=\s*[\"']([^\"']+)", text, re.IGNORECASE
            )
            if match:
                python_constraint = match.group(1).strip()

    for rel, path in relative_files:
        if not rel.endswith(".py"):
            continue
        name = path.name
        if (
            name == "conftest.py"
            or name.startswith("test_")
            or name.endswith("_test.py")
        ):
            text = _read_text(path)
            if name == "conftest.py" or re.search(
                r"(^|\n)\s*(from\s+pytest\s+import|import\s+pytest\b)", text
            ):
                pytest_evidence.append(rel)

    test_candidates = _unique(
        rel.split("/", 1)[0]
        for rel in python_files
        if Path(rel).name.startswith("test_")
        or Path(rel).name.endswith("_test.py")
        or Path(rel).name == "conftest.py"
    )
    source_candidates = _unique(
        rel.split("/", 1)[0]
        for rel in python_files
        if "/" in rel and rel.split("/", 1)[0] not in set(test_candidates)
    )
    runner = _detect_pytest_runner(relative_files, _unique(pytest_evidence))
    return {
        "label": label,
        "file_paths": [rel for rel, _ in relative_files],
        "python_detected": bool(python_files),
        "pytest_detected": bool(pytest_evidence),
        "python_constraint": python_constraint,
        "python_evidence": _unique(python_evidence),
        "pytest_evidence": _unique(pytest_evidence),
        "pytest_runner": runner,
        "source_candidates": source_candidates,
        "test_candidates": test_candidates,
        "file_count": len(files),
    }


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _root_identity(root: Path) -> Dict[str, object]:
    info = os.stat(str(root), follow_symlinks=False)
    return {
        "resolved_path_sha256": hashlib.sha256(str(root).encode("utf-8")).hexdigest(),
        "device": info.st_dev,
        "inode": info.st_ino,
    }


def build_scope(
    project_root: Path, extras: Sequence[Tuple[str, Path]]
) -> Dict[str, object]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "init-tide-scope",
        "project_root": str(project_root),
        "target_root_identity": _root_identity(project_root),
        "extra_sources": [
            {"label": label, "path": str(path), "root_identity": _root_identity(path)}
            for label, path in extras
        ],
    }  # type: Dict[str, object]
    payload["scope_digest"] = _canonical_digest(payload)
    return payload


def load_scope(
    path: Path, confirmed_digest: str
) -> Tuple[Path, List[Tuple[str, Path]]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("读取范围计划必须是普通文件")
    if not _is_within(path.resolve(strict=True), Path(tempfile.gettempdir()).resolve()):
        raise ValueError("读取范围计划必须位于系统临时目录")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("读取范围计划不是有效 JSON：{}".format(exc))
    expected = {
        "schema_version",
        "kind",
        "project_root",
        "target_root_identity",
        "extra_sources",
        "scope_digest",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("读取范围计划字段无效")
    without_digest = dict(value)
    digest = without_digest.pop("scope_digest")
    if digest != _canonical_digest(without_digest) or digest != confirmed_digest:
        raise ValueError("读取范围计划摘要无效或未经当前确认")
    project = _resolve_directory(value["project_root"], "目标项目")
    if value["target_root_identity"] != _root_identity(project):
        raise ValueError("目标项目在确认后发生变化")
    extras = []  # type: List[Tuple[str, Path]]
    if not isinstance(value["extra_sources"], list):
        raise ValueError("额外源码范围无效")
    for item in value["extra_sources"]:
        if not isinstance(item, dict) or set(item) != {
            "label",
            "path",
            "root_identity",
        }:
            raise ValueError("额外源码范围项无效")
        label = item["label"]
        if not isinstance(label, str) or not re.fullmatch(
            r"[a-z][a-z0-9-]{0,31}", label
        ):
            raise ValueError("额外源码标签无效")
        source = _resolve_directory(item["path"], "额外源码 {}".format(label))
        if item["root_identity"] != _root_identity(source):
            raise ValueError("额外源码在确认后发生变化：{}".format(label))
        extras.append((label, source))
    return project, extras


def build_result(
    project_root: Path, extras: Sequence[Tuple[str, Path]]
) -> Dict[str, object]:
    project = _scan_root(project_root, "current-project")
    extra_results = [_scan_root(path, label) for label, path in extras]
    supported = bool(project["python_detected"] and project["pytest_detected"])
    result = {
        "schema_version": SCHEMA_VERSION,
        "project_kind": "python-pytest" if supported else "unsupported",
        "target_root_identity": _root_identity(project_root),
        "project": project,
        "extra_sources": extra_results,
    }  # type: Dict[str, object]
    result["scan_digest"] = _canonical_digest(result)
    return result


def _write_json(result: Dict[str, object], output: str) -> None:
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output == "-":
        sys.stdout.write(rendered)
        return
    destination = Path(output)
    if destination.is_symlink() or destination.exists():
        raise ValueError("拒绝覆盖既有扫描输出")
    if destination.parent.is_symlink() or not destination.parent.is_dir():
        raise ValueError("扫描输出目录必须是已存在的普通目录")
    temp_root = Path(tempfile.gettempdir()).resolve()
    parent = destination.parent.resolve(strict=True)
    try:
        parent.relative_to(temp_root)
    except ValueError:
        raise ValueError("扫描输出必须位于系统临时目录")
    parent_fd = os.open(str(parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptor = None
    try:
        descriptor = os.open(
            destination.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = None
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(parent_fd)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)


def _self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="init-tide-scan-") as temp_dir:
        root = Path(temp_dir)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.8"\n'
            '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
            encoding="utf-8",
        )
        (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
        (root / "src" / "client.py").write_text(
            "class Client:\n    pass\n", encoding="utf-8"
        )
        (root / "tests" / "test_client.py").write_text(
            "import pytest\n", encoding="utf-8"
        )
        (root / ".env").write_text("PASSWORD=secret\n", encoding="utf-8")
        (root / "captured.har").write_text("{}\n", encoding="utf-8")
        result = build_result(root.resolve(), [])
        assert result["project_kind"] == "python-pytest"
        rendered = json.dumps(result, ensure_ascii=False)
        assert str(root) not in rendered
        assert result["scan_digest"]
        assert result["project"]["pytest_runner"] == {  # type: ignore[index]
            "argv_prefix": ["uv", "run", "--locked", "--no-sync", "python"],
            "status": "confirmed",
            "evidence": ["uv.lock", "pyproject.toml"],
        }
        assert ".env" not in result["project"]["file_paths"]  # type: ignore[index]
        assert "captured.har" not in result["project"]["file_paths"]  # type: ignore[index]
        scope = build_scope(root.resolve(), [])
        scope_path = root / "scope.json"
        _write_json(scope, str(scope_path))
        loaded_root, loaded_extras = load_scope(scope_path, str(scope["scope_digest"]))
        assert loaded_root == root.resolve() and not loaded_extras
    print("scan_project.py 自检通过")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.self_test:
        return _self_test()
    try:
        if args.prepare_scope:
            if args.output == "-":
                raise ValueError("读取范围计划必须写入系统临时目录，不能输出到终端")
            project_root = _resolve_directory(args.project_root, "目标项目")
            extras = _parse_extra(args.extra_source)
            scope = build_scope(project_root, extras)
            _write_json(scope, args.output)
            print("读取范围计划已生成；确认摘要：{}".format(scope["scope_digest"]))
            return 0
        if not args.scope_plan or not args.confirmed_scope_digest:
            raise ValueError("扫描前必须提供已确认的读取范围计划")
        if args.extra_source:
            raise ValueError("实际扫描不接受未绑定的 --extra-source")
        project_root, extras = load_scope(
            Path(args.scope_plan), args.confirmed_scope_digest
        )
        result = build_result(project_root, extras)
        _write_json(result, args.output)
        if result["project_kind"] != "python-pytest":
            print("未同时发现 Python 与 pytest 的明确证据，停止初始化", file=sys.stderr)
            return 2
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("扫描失败：{}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
