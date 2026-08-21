#!/usr/bin/env python3
"""把用户确认的初始化计划安全写入新的 .tide 目录。"""

import argparse
import ctypes
import errno
import hashlib
import json
import os
import secrets
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Sequence, cast

SCHEMA_VERSION = "1.0"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="仅在计划摘要完全匹配时，将项目画像与规则写入新的 .tide 目录。"
    )
    parser.add_argument("--project-root", required=False, help="待初始化项目根目录。")
    parser.add_argument("--plan", help="bind_init_plan.py 生成的初始化计划。")
    parser.add_argument(
        "--confirmed-plan-digest", help="用户明确确认的计划 SHA-256 摘要。"
    )
    parser.add_argument("--self-test", action="store_true", help="运行隔离自检后退出。")
    return parser


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


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


def _load_plan(path: Path) -> Dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("计划必须是普通 JSON 文件")
    temp_root = Path(tempfile.gettempdir()).resolve()
    try:
        path.resolve(strict=True).relative_to(temp_root)
    except ValueError:
        raise ValueError("计划必须位于系统临时目录")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(path), flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("计划必须是普通 JSON 文件")
        with os.fdopen(descriptor, "r", encoding="utf-8", closefd=False) as handle:
            value = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
    finally:
        os.close(descriptor)
    if not isinstance(value, dict):
        raise ValueError("计划顶层必须是 JSON 对象")
    return value


def _reject_duplicate_keys(pairs: Sequence[object]) -> Dict[str, object]:
    value = {}  # type: Dict[str, object]
    for pair in pairs:
        key, child = pair  # type: ignore[misc]
        if key in value:
            raise ValueError("计划 JSON 包含重复字段：{}".format(key))
        value[key] = child
    return value


def _rename_no_replace_at(parent_fd: int, source: str, target: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    target_bytes = os.fsencode(target)
    if sys.platform == "darwin" and hasattr(libc, "renameatx_np"):
        result = libc.renameatx_np(
            parent_fd, source_bytes, parent_fd, target_bytes, 0x00000004
        )
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        result = libc.renameat2(parent_fd, source_bytes, parent_fd, target_bytes, 1)
    else:
        raise ValueError("当前系统不支持原子且禁止覆盖的目录发布")
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in (errno.EEXIST, errno.ENOTEMPTY):
            raise ValueError("目标项目已存在 .tide，拒绝覆盖或合并")
        raise OSError(error_number, os.strerror(error_number))


def _validate_rule_path(raw_path: object) -> PurePosixPath:
    if not isinstance(raw_path, str):
        raise ValueError("规则路径必须是字符串")
    path = PurePosixPath(raw_path)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ValueError("规则路径越界：{}".format(raw_path))
    if path.suffix.lower() != ".md" or any(part.startswith(".") for part in path.parts):
        raise ValueError("规则路径必须是非隐藏 Markdown 文件：{}".format(raw_path))
    return path


def _validate_plan(root: Path, plan: Dict[str, object], confirmed_digest: str) -> None:
    if plan.get("schema_version") != SCHEMA_VERSION or plan.get("kind") != "init-tide":
        raise ValueError("计划类型或版本无效")
    stored_digest = plan.get("plan_digest")
    payload = dict(plan)
    payload.pop("plan_digest", None)
    actual_digest = _digest(payload)
    if not isinstance(stored_digest, str) or stored_digest != actual_digest:
        raise ValueError("计划内容摘要无效")
    if confirmed_digest != stored_digest:
        raise ValueError("确认摘要与当前计划不匹配")
    if plan.get("target_root_identity") != _root_identity(root):
        raise ValueError("目标项目根目录与绑定计划不一致")
    profile = plan.get("profile")
    if not isinstance(profile, dict):
        raise ValueError("计划缺少项目画像")
    profile_bytes = _canonical(profile) + b"\n"
    if plan.get("profile_sha256") != hashlib.sha256(profile_bytes).hexdigest():
        raise ValueError("项目画像摘要无效")
    rules = plan.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("计划至少需要一个规则文件")
    seen = set()
    for item in rules:
        if not isinstance(item, dict):
            raise ValueError("规则计划项必须是 JSON 对象")
        relative = _validate_rule_path(item.get("path"))
        if relative.as_posix() in seen:
            raise ValueError("规则路径重复：{}".format(relative.as_posix()))
        seen.add(relative.as_posix())
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("规则内容不能为空：{}".format(relative.as_posix()))
        if item.get("sha256") != hashlib.sha256(content.encode("utf-8")).hexdigest():
            raise ValueError("规则摘要无效：{}".format(relative.as_posix()))
    summary = plan.get("confirmation_summary")
    expected_summary = {
        "project_kind": "python-pytest",
        "profile_sha256": plan.get("profile_sha256"),
        "project_analysis_sha256": plan.get("project_analysis_sha256"),
        "test_analysis_sha256": plan.get("test_analysis_sha256"),
        "review_sha256": plan.get("review_sha256"),
        "rule_files": [
            {"path": item["path"], "sha256": item["sha256"]} for item in rules
        ],
        "write_targets": [".tide/project-profile.json", ".tide/rules/"],
    }
    if summary != expected_summary:
        raise ValueError("确认摘要与计划内容不一致")
    for field in ("project_analysis_sha256", "test_analysis_sha256", "review_sha256"):
        digest = plan.get(field)
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("计划未绑定有效的角色结果：{}".format(field))


def _directory_flags() -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ValueError("当前系统不支持安全目录文件描述符操作")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _open_directory_at(parent_fd: int, name: str) -> int:
    return os.open(name, _directory_flags(), dir_fd=parent_fd)


def _write_new_at(parent_fd: int, name: str, content: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = os.open(name, flags, 0o600, dir_fd=parent_fd)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def _ensure_directories_at(parent_fd: int, parts: Sequence[str]) -> int:
    current_fd = os.dup(parent_fd)
    try:
        for part in parts:
            try:
                os.mkdir(part, 0o700, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = _open_directory_at(current_fd, part)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _remove_tree_at(parent_fd: int, name: str) -> None:
    directory_fd = _open_directory_at(parent_fd, name)
    try:
        for child in os.listdir(directory_fd):
            child_stat = os.stat(child, dir_fd=directory_fd, follow_symlinks=False)
            if stat.S_ISDIR(child_stat.st_mode):
                _remove_tree_at(directory_fd, child)
            else:
                os.unlink(child, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)
    os.rmdir(name, dir_fd=parent_fd)


def apply_plan(
    root: Path, plan: Dict[str, object], confirmed_digest: str
) -> Dict[str, object]:
    _validate_plan(root, plan, confirmed_digest)
    expected_root_identity = _root_identity(root)
    root_fd = os.open(str(root), _directory_flags())
    stage_fd = None  # type: Optional[int]
    stage_name = ".tide-staging-{}".format(secrets.token_hex(12))
    published = False
    try:
        root_stat = os.fstat(root_fd)
        opened_identity = {
            "resolved_path_sha256": hashlib.sha256(
                str(root).encode("utf-8")
            ).hexdigest(),
            "device": root_stat.st_dev,
            "inode": root_stat.st_ino,
        }
        if opened_identity != expected_root_identity:
            raise ValueError("目标项目根目录在打开时发生替换")
        try:
            os.stat(".tide", dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError("目标项目已存在 .tide，拒绝覆盖或合并")
        os.mkdir(stage_name, 0o700, dir_fd=root_fd)
        stage_fd = _open_directory_at(root_fd, stage_name)
        os.mkdir("rules", 0o700, dir_fd=stage_fd)
        stage_rules_fd = _open_directory_at(stage_fd, "rules")
        rules = plan["rules"]  # type: ignore[index]
        try:
            for item in rules:  # type: ignore[union-attr]
                relative = _validate_rule_path(item["path"])
                parent_fd = _ensure_directories_at(stage_rules_fd, relative.parts[:-1])
                try:
                    _write_new_at(
                        parent_fd, relative.name, item["content"].encode("utf-8")
                    )
                finally:
                    os.close(parent_fd)
            os.fsync(stage_rules_fd)
        finally:
            os.close(stage_rules_fd)
        profile_bytes = _canonical(plan["profile"]) + b"\n"
        _write_new_at(stage_fd, "project-profile.json", profile_bytes)
        os.fsync(stage_fd)

        current_root_stat = os.fstat(root_fd)
        if (
            current_root_stat.st_dev != root_stat.st_dev
            or current_root_stat.st_ino != root_stat.st_ino
        ):
            raise ValueError("目标项目根目录在发布前发生替换")
        os.close(stage_fd)
        stage_fd = None
        _rename_no_replace_at(root_fd, stage_name, ".tide")
        os.fsync(root_fd)
        published = True
    finally:
        if stage_fd is not None:
            os.close(stage_fd)
        if not published:
            try:
                _remove_tree_at(root_fd, stage_name)
            except FileNotFoundError:
                pass
        os.close(root_fd)

    result = {
        "status": "initialized",
        "plan_digest": confirmed_digest,
        "profile": ".tide/project-profile.json",
        "rules": [".tide/rules/{}".format(item["path"]) for item in plan["rules"]],  # type: ignore[index]
    }
    return result


def _make_plan(root: Path) -> Dict[str, object]:
    profile = {
        "schema_version": SCHEMA_VERSION,
        "project_kind": "python-pytest",
        "evidence": ["pytest.ini"],
    }
    content = "# 已确认约定\n\n- 证据：pytest.ini\n"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "init-tide",
        "target_root_identity": _root_identity(root),
        "scan_digest": "0" * 64,
        "profile": profile,
        "profile_sha256": hashlib.sha256(_canonical(profile) + b"\n").hexdigest(),
        "rules": [
            {
                "path": "observed-conventions.md",
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "content": content,
            }
        ],
        "review_sha256": hashlib.sha256("结论：通过\n".encode("utf-8")).hexdigest(),
        "project_analysis_sha256": "1" * 64,
        "test_analysis_sha256": "2" * 64,
    }  # type: Dict[str, object]
    payload["confirmation_summary"] = {
        "project_kind": "python-pytest",
        "profile_sha256": payload["profile_sha256"],
        "project_analysis_sha256": payload["project_analysis_sha256"],
        "test_analysis_sha256": payload["test_analysis_sha256"],
        "review_sha256": payload["review_sha256"],
        "rule_files": [
            {"path": item["path"], "sha256": item["sha256"]}
            for item in cast(List[Dict[str, object]], payload["rules"])
        ],  # type: ignore[index]
        "write_targets": [".tide/project-profile.json", ".tide/rules/"],
    }
    payload["plan_digest"] = _digest(payload)
    return payload


def _self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="init-tide-apply-") as temp_dir:
        root = Path(temp_dir).resolve()
        plan = _make_plan(root)
        digest = str(plan["plan_digest"])
        result = apply_plan(root, plan, digest)
        assert result["status"] == "initialized"
        assert (root / ".tide" / "project-profile.json").is_file()
        assert (root / ".tide" / "rules" / "observed-conventions.md").is_file()
        try:
            apply_plan(root, plan, digest)
        except ValueError:
            pass
        else:
            raise AssertionError("重复初始化必须失败关闭")
    print("apply_init_plan.py 自检通过")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.self_test:
        return _self_test()
    if not args.project_root or not args.plan or not args.confirmed_plan_digest:
        print("写入失败：除 --self-test 外，所有参数均为必填", file=sys.stderr)
        return 2
    try:
        root = _validate_root(args.project_root)
        plan = _load_plan(Path(args.plan))
        result = apply_plan(root, plan, args.confirmed_plan_digest)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
        print("写入失败：{}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
