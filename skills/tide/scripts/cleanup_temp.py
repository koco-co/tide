#!/usr/bin/env python3
"""只删除 Tide 在系统临时根目录中创建的本次专用目录。"""

import argparse
import os
import sys
import tempfile
from pathlib import Path


class CleanupError(Exception):
    pass


def create():
    return Path(tempfile.mkdtemp(prefix="tide-run-")).resolve()


def cleanup(path):
    temp_root = Path(tempfile.gettempdir()).resolve()
    if path.is_symlink():
        raise CleanupError("临时目录不能是符号链接。")
    resolved = path.resolve(strict=True)
    try:
        relative = resolved.relative_to(temp_root)
    except ValueError:
        raise CleanupError("拒绝删除系统临时根目录之外的路径。")
    if len(relative.parts) != 1 or not relative.name.startswith(
        ("tide-", "init-tide-")
    ):
        raise CleanupError("只允许删除本次 Tide 专用临时目录。")
    if not resolved.is_dir():
        raise CleanupError("清理目标必须是目录。")
    for current, dirs, files in os.walk(
        str(resolved), topdown=False, followlinks=False
    ):
        current_path = Path(current)
        for name in files:
            target = current_path / name
            if target.is_symlink() or target.is_file():
                target.unlink()
            else:
                raise CleanupError("临时目录包含特殊文件，停止清理。")
        for name in dirs:
            target = current_path / name
            if target.is_symlink():
                target.unlink()
            else:
                target.rmdir()
    resolved.rmdir()


def self_test():
    root = create()
    (root / "nested").mkdir()
    (root / "nested" / "value.json").write_text("{}\n", encoding="utf-8")
    cleanup(root)
    if root.exists():
        raise CleanupError("自检未清理临时目录。")


def parser():
    value = argparse.ArgumentParser(description="安全清理本次 Tide 系统临时目录。")
    value.add_argument("path", nargs="?", help="Tide 本次专用临时目录")
    value.add_argument("--create", action="store_true", help="创建并输出专用临时目录")
    value.add_argument("--self-test", action="store_true", help="运行隔离自检")
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print("cleanup_temp.py 自检通过。")
            return 0
        if args.create:
            if args.path:
                raise CleanupError("创建临时目录时不能同时提供清理路径。")
            print(create())
            return 0
        if not args.path:
            raise CleanupError("必须提供清理目录。")
        cleanup(Path(args.path))
        print("Tide 临时目录已清理。")
        return 0
    except (OSError, CleanupError) as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
