#!/usr/bin/env python3
"""使用项目画像已确认的 runner 启动 Tide pytest 执行器。"""

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

RUNNER_PROFILE_ENV = "TIDE_RUNNER_PROFILE_SHA256"
RUNNER_PREFIX_ENV = "TIDE_RUNNER_PREFIX_SHA256"
SAFE_PREFIXES = {
    ("uv", "run", "--locked", "--no-sync", "python"): "uv.lock",
    ("poetry", "run", "python"): "poetry.lock",
    ("pipenv", "run", "python"): "Pipfile.lock",
    ("pdm", "run", "python"): "pdm.lock",
}
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
ENV_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")


class LaunchError(Exception):
    pass


def _read_profile(root):
    path = root / ".tide" / "project-profile.json"
    info = os.lstat(str(path))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise LaunchError("项目画像必须是普通文件。")
    raw = path.read_bytes()
    try:
        profile = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise LaunchError("项目画像不是有效 JSON：%s" % exc)
    runner = profile.get("pytest_runner") if isinstance(profile, dict) else None
    prefix = runner.get("argv_prefix") if isinstance(runner, dict) else None
    if not isinstance(prefix, list) or any(
        not isinstance(item, str) for item in prefix
    ):
        raise LaunchError("项目画像缺少 runner。")
    prefix_tuple = tuple(prefix)
    lock_name = SAFE_PREFIXES.get(prefix_tuple)
    if (
        not isinstance(runner, dict)
        or runner.get("status") != "confirmed"
        or lock_name is None
    ):
        raise LaunchError("项目 runner 未确认或不在安全启动器支持范围内。")
    lock_path = root / lock_name
    if lock_path.is_symlink() or not lock_path.is_file():
        raise LaunchError("项目 runner 缺少对应锁文件。")
    if shutil.which(prefix[0]) is None:
        raise LaunchError("当前环境找不到项目 runner：%s" % prefix[0])
    runtime_variables = profile.get("runtime_environment_variables")
    if not isinstance(runtime_variables, list):
        raise LaunchError("项目画像缺少运行环境变量声明。")
    declared_names = []
    for item in runtime_variables:
        if not isinstance(item, dict) or item.get("status") != "confirmed":
            continue
        name = item.get("name")
        if not isinstance(name, str) or not ENV_NAME_PATTERN.fullmatch(name):
            raise LaunchError("项目画像包含无效环境变量名。")
        if name not in declared_names:
            declared_names.append(name)
    return raw, prefix, declared_names


def _runner_environment(temporary_root, declared_names):
    allowed = (
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TZ",
        "TMPDIR",
        "PYTHONPATH",
        "SYSTEMROOT",
    )
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    for name in declared_names:
        if name in os.environ:
            environment[name] = os.environ[name]
    cache_root = Path(temporary_root) / "tool-cache"
    uv_cache = cache_root / "uv"
    xdg_cache = cache_root / "xdg"
    uv_cache.mkdir(parents=True, exist_ok=False)
    xdg_cache.mkdir(parents=True, exist_ok=False)
    environment["UV_CACHE_DIR"] = str(uv_cache)
    environment["XDG_CACHE_HOME"] = str(xdg_cache)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _require_prepared_runner(root, prefix):
    if tuple(prefix) != ("uv", "run", "--locked", "--no-sync", "python"):
        return
    environment_dir = root / ".venv"
    try:
        environment_info = os.lstat(str(environment_dir))
    except FileNotFoundError:
        raise LaunchError(
            "项目 uv runner 环境尚未准备；为避免自动创建 .venv，Tide 已阻断执行。"
        )
    if stat.S_ISLNK(environment_info.st_mode) or not stat.S_ISDIR(
        environment_info.st_mode
    ):
        raise LaunchError("项目 .venv 必须是现有真实目录，不能是软链接。")
    configuration = environment_dir / "pyvenv.cfg"
    executables = (
        environment_dir / "bin" / "python",
        environment_dir / "Scripts" / "python.exe",
    )
    if (
        configuration.is_symlink()
        or not configuration.is_file()
        or not any(path.exists() and path.resolve().is_file() for path in executables)
    ):
        raise LaunchError("项目 .venv 不完整，拒绝由 Tide 自动创建或修复。")


def launch(root, forwarded):
    if root.is_symlink() or not root.resolve(strict=True).is_dir():
        raise LaunchError("项目根目录无效。")
    root = root.resolve(strict=True)
    profile_bytes, prefix, declared_names = _read_profile(root)
    _require_prepared_runner(root, prefix)
    runner_script = Path(__file__).resolve().parent / "run_pytest.py"
    if runner_script.is_symlink() or not runner_script.is_file():
        raise LaunchError("Tide 执行器不可用。")
    profile_sha256 = hashlib.sha256(profile_bytes).hexdigest()
    prefix_sha256 = hashlib.sha256(
        json.dumps(prefix, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    command = prefix + [str(runner_script), "--project-root", str(root)] + forwarded
    with tempfile.TemporaryDirectory(prefix="tide-runner-") as directory:
        environment = _runner_environment(Path(directory), declared_names)
        environment[RUNNER_PROFILE_ENV] = profile_sha256
        environment[RUNNER_PREFIX_ENV] = prefix_sha256
        completed = subprocess.run(
            command,
            cwd=str(root),
            env=environment,
            stdin=subprocess.DEVNULL,
            shell=False,
            check=False,
        )
    return completed.returncode


def self_test():
    if not HASH_PATTERN.fullmatch(hashlib.sha256(b"profile").hexdigest()):
        raise LaunchError("自检无法计算画像摘要。")
    if ("uv", "run", "python") in SAFE_PREFIXES:
        raise LaunchError("自检发现缺少锁定参数的 uv runner 被允许。")
    with tempfile.TemporaryDirectory(prefix="tide-launch-test-") as directory:
        declared_name = "TIDE_SELF_TEST_DECLARED"
        unbound_name = "TIDE_SELF_TEST_UNBOUND"
        previous_declared = os.environ.get(declared_name)
        previous_unbound = os.environ.get(unbound_name)
        try:
            os.environ[declared_name] = "declared-value"
            os.environ[unbound_name] = "must-not-pass"
            environment = _runner_environment(Path(directory), [declared_name])
        finally:
            if previous_declared is None:
                os.environ.pop(declared_name, None)
            else:
                os.environ[declared_name] = previous_declared
            if previous_unbound is None:
                os.environ.pop(unbound_name, None)
            else:
                os.environ[unbound_name] = previous_unbound
        if environment.get(declared_name) != "declared-value":
            raise LaunchError("自检未透传画像已确认的环境变量。")
        if unbound_name in environment:
            raise LaunchError("自检错误透传了画像未确认的环境变量。")
        temporary_root = Path(directory).resolve()
        for name in ("UV_CACHE_DIR", "XDG_CACHE_HOME"):
            cache_path = Path(environment[name]).resolve()
            if os.path.commonpath((str(temporary_root), str(cache_path))) != str(
                temporary_root
            ):
                raise LaunchError("自检发现 runner 缓存越过一次性临时目录。")
        runner_root = Path(directory) / "runner-project"
        runner_root.mkdir()
        try:
            _require_prepared_runner(
                runner_root,
                ["uv", "run", "--locked", "--no-sync", "python"],
            )
        except LaunchError:
            pass
        else:
            raise LaunchError("自检未阻断缺少既有 .venv 的 uv runner。")


def parser():
    value = argparse.ArgumentParser(
        description="使用项目画像已确认的 runner 启动 run_pytest.py。",
        add_help=False,
    )
    value.add_argument("--project-root")
    value.add_argument("--self-test", action="store_true")
    value.add_argument("--help", action="store_true")
    return value


def main(argv=None):
    raw = list(sys.argv[1:] if argv is None else argv)
    args, forwarded = parser().parse_known_args(raw)
    if forwarded[:1] == ["--"]:
        forwarded = forwarded[1:]
    try:
        if args.help:
            print("用法：launch_pytest.py --project-root <目录> [run_pytest.py 参数]")
            return 0
        if args.self_test:
            self_test()
            print("launch_pytest.py 自检通过。")
            return 0
        if not args.project_root:
            raise LaunchError("必须提供 --project-root。")
        return launch(Path(args.project_root), forwarded)
    except (OSError, LaunchError) as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
