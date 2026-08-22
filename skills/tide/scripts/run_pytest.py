#!/usr/bin/env python3
"""在独立确认和安全环境门禁后执行精确 pytest 节点。"""

import argparse
import hashlib
import importlib.util
import ipaddress
import json
import os
import re
import socket
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

SAFE_ENVIRONMENTS = {
    "local",
    "dev",
    "development",
    "test",
    "testing",
    "qa",
    "staging",
    "sandbox",
}
BLOCKED_ENVIRONMENTS = {"", "unknown", "prod", "production"}
RUN_ID_PATTERN = re.compile(r"tide-[a-z0-9][a-z0-9-]{5,63}")
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
ENV_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
FORBIDDEN_ENV_NAMES = {
    "HOME",
    "PATH",
    "PYTHONHOME",
    "PYTHONPATH",
    "SYSTEMROOT",
    "TIDE_EXECUTION_ENV",
    "TMPDIR",
    "VIRTUAL_ENV",
    "TIDE_VENV_IDENTITY_SHA256",
}
RUNNER_PROFILE_ENV = "TIDE_RUNNER_PROFILE_SHA256"
RUNNER_PREFIX_ENV = "TIDE_RUNNER_PREFIX_SHA256"
VENV_IDENTITY_ENV = "TIDE_VENV_IDENTITY_SHA256"
SAFE_RUNNER_PREFIXES = {
    ("uv", "run", "--locked", "--no-sync", "python"),
    ("poetry", "run", "python"),
    ("pipenv", "run", "python"),
    ("pdm", "run", "python"),
}


class ExecutionError(Exception):
    pass


def _sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    with open(str(path), "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def _check_root(root):
    try:
        info = os.lstat(str(root))
    except OSError as exc:
        raise ExecutionError("目标项目根目录不可用：%s" % exc)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ExecutionError("目标项目根目录必须是真实目录，不能是软链接。")
    return root.resolve()


def _validate_project_python(root):
    environment_dir = root / ".venv"
    try:
        info = os.lstat(str(environment_dir))
        expected_prefix = environment_dir.resolve(strict=True)
        actual_prefix = Path(sys.prefix).resolve(strict=True)
    except OSError as exc:
        raise ExecutionError("无法验证项目 .venv：%s" % exc)
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISDIR(info.st_mode)
        or actual_prefix != expected_prefix
    ):
        raise ExecutionError("当前执行器不是由目标项目 .venv Python 启动。")
    payload = {
        "resolved_path": str(expected_prefix),
        "device": info.st_dev,
        "inode": info.st_ino,
    }
    identity = hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    if os.environ.get(VENV_IDENTITY_ENV) != identity:
        raise ExecutionError("当前项目 .venv 身份未由启动器绑定。")
    return identity


def _directory_flags():
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ExecutionError("当前系统不支持安全目录文件描述符操作。")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _open_directory_path(root_fd, relative):
    current_fd = os.dup(root_fd)
    traversed = Path()
    try:
        for part in relative.parts:
            traversed = traversed / part
            try:
                next_fd = os.open(part, _directory_flags(), dir_fd=current_fd)
            except OSError as exc:
                raise ExecutionError("无法打开安全目录 %s：%s" % (traversed, exc))
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _read_regular_at(root_fd, relative, label, max_bytes):
    parent_fd = _open_directory_path(root_fd, relative.parent)
    descriptor = None
    try:
        descriptor = os.open(
            relative.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd
        )
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ExecutionError("%s必须是普通文件，不能是软链接。" % label)
        if info.st_size > max_bytes:
            raise ExecutionError("%s超过大小限制。" % label)
        chunks = []
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > max_bytes:
            raise ExecutionError("%s超过大小限制。" % label)
        return data
    except OSError as exc:
        raise ExecutionError("无法读取%s：%s" % (label, exc))
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)


def _atomic_create_at(parent_fd, name, data):
    temporary_name = ".tide-execution-%d-%d" % (os.getpid(), time.time_ns())
    descriptor = None
    try:
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(
            temporary_name,
            name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
        os.unlink(temporary_name, dir_fd=parent_fd)
        temporary_name = None
        os.fsync(parent_fd)
    except OSError as exc:
        raise ExecutionError("创建执行记录失败：%s" % exc)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_name is not None:
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass


def _relative_path(value, label):
    path = Path(str(value))
    if (
        path.is_absolute()
        or not path.parts
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ExecutionError("%s必须是规范的项目内相对路径。" % label)
    return path


def _reject_duplicate_keys(pairs):
    value = {}
    for key, child in pairs:
        if key in value:
            raise ExecutionError("JSON 包含重复字段：%s" % key)
        value[key] = child
    return value


def _load_manifest(root_fd, run_id):
    run_relative = Path(".tide") / "runs" / run_id
    manifest_relative = run_relative / "manifest.json"
    try:
        manifest_bytes = _read_regular_at(
            root_fd, manifest_relative, "运行清单", 2 * 1024 * 1024
        )
        manifest = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeError, ValueError) as exc:
        raise ExecutionError("运行清单不是有效 JSON：%s" % exc)
    if not isinstance(manifest, dict) or manifest.get("run_id") != run_id:
        raise ExecutionError("运行清单与运行编号不一致。")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ExecutionError("运行清单没有生成文件。")
    generated = {}
    for item in files:
        if not isinstance(item, dict) or set(item) != {"relative_path", "sha256"}:
            raise ExecutionError("运行清单文件记录无效。")
        relative = _relative_path(item["relative_path"], "生成文件")
        expected_hash = item["sha256"]
        if not isinstance(expected_hash, str) or not HASH_PATTERN.fullmatch(
            expected_hash
        ):
            raise ExecutionError("运行清单包含无效文件散列。")
        actual_hash = hashlib.sha256(
            _read_regular_at(root_fd, relative, "生成文件", 2 * 1024 * 1024)
        ).hexdigest()
        if actual_hash != expected_hash:
            raise ExecutionError("生成文件内容已经变化，拒绝执行：%s" % relative)
        generated[str(relative)] = expected_hash
    return manifest, generated, run_relative, hashlib.sha256(manifest_bytes).hexdigest()


def _validate_environment(value):
    normalized = str(value or "").strip().lower()
    if normalized in BLOCKED_ENVIRONMENTS:
        raise ExecutionError("production、prod、unknown 或空环境永久阻断执行。")
    if normalized not in SAFE_ENVIRONMENTS:
        raise ExecutionError("环境未在允许列表中，拒绝执行：%s" % normalized)
    return normalized


def _resolve_addresses(hostname, port):
    try:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ExecutionError("目标主机解析失败：%s" % exc)
    addresses = sorted({str(record[4][0]).split("%", 1)[0] for record in records})
    if not addresses:
        raise ExecutionError("目标主机没有可用地址。")
    parsed = []
    for value in addresses:
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            raise ExecutionError("目标主机返回无效地址。")
        if address.is_unspecified or address.is_multicast or address.is_reserved:
            raise ExecutionError("目标主机解析到禁止地址。")
        parsed.append(address)
    return parsed


def _validate_target_url(value, environment, allow_public_target):
    try:
        parsed = urlsplit(str(value))
    except ValueError as exc:
        raise ExecutionError("目标地址无效：%s" % exc)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ExecutionError("目标地址必须是包含主机的 http 或 https 地址。")
    if parsed.username or parsed.password:
        raise ExecutionError("目标地址不得包含用户名或密码。")
    if parsed.query or parsed.fragment:
        raise ExecutionError("目标地址不得包含查询参数或片段。")
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        raise ExecutionError(
            "真实执行只接受字面 IP 目标；"
            "脚本无法把域名解析强制绑定到测试客户端 transport。"
        )
    normalized = parsed.geturl()
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise ExecutionError("目标端口无效：%s" % exc)
    addresses = _resolve_addresses(parsed.hostname, port)
    if environment == "local" and any(not address.is_loopback for address in addresses):
        raise ExecutionError("local 环境只允许全部解析为回环地址的目标。")
    has_public = any(
        not (address.is_loopback or address.is_private or address.is_link_local)
        for address in addresses
    )
    if has_public and not allow_public_target:
        raise ExecutionError("公共网络目标必须经过单独显式授权。")
    return (
        hashlib.sha256(parsed.hostname.lower().encode("utf-8")).hexdigest(),
        hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        normalized,
        addresses,
    )


def _validate_nodes(nodes, generated):
    if not nodes:
        raise ExecutionError("至少需要一个用户确认的精确 pytest 节点。")
    validated = []
    for node in nodes:
        if (
            not isinstance(node, str)
            or not node.strip()
            or any(character in node for character in ("\n", "\r", "\x00"))
        ):
            raise ExecutionError("pytest 节点格式无效。")
        file_part = node.split("::", 1)[0]
        relative = _relative_path(file_part, "pytest 节点文件")
        if str(relative) not in generated:
            raise ExecutionError("pytest 节点不属于本次生成文件：%s" % node)
        validated.append(node)
    if len(set(validated)) != len(validated):
        raise ExecutionError("pytest 节点列表包含重复项。")
    return validated


def _runtime_env_vars(manifest, target_env_var):
    names = manifest.get("runtime_env_vars")
    if not isinstance(names, list) or len(names) > 32:
        raise ExecutionError("运行清单缺少有效的必需环境变量名数组。")
    validated = []
    for index, name in enumerate(names):
        if (
            not isinstance(name, str)
            or not ENV_NAME_PATTERN.fullmatch(name)
            or name.upper() in FORBIDDEN_ENV_NAMES
            or name.upper() == target_env_var.upper()
            or name in validated
        ):
            raise ExecutionError("运行清单中的环境变量名无效：第 %d 项。" % index)
        validated.append(name)
    missing = [
        name for name in validated if name not in os.environ or not os.environ[name]
    ]
    if missing:
        raise ExecutionError("当前执行环境缺少必需变量：%s。" % "、".join(missing))
    return validated


def _safe_environment(target_env_var, target_url, environment_name, runtime_env_vars):
    allowed = (
        "PATH",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TZ",
        "TMPDIR",
        "SYSTEMROOT",
    )
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    environment[target_env_var] = target_url
    environment["TIDE_EXECUTION_ENV"] = environment_name
    for name in runtime_env_vars:
        environment[name] = os.environ[name]
    return environment


def _execution_digest(
    run_id,
    environment,
    target_url_sha256,
    target_env_var,
    runtime_env_vars,
    nodes,
    generated,
    manifest_sha256,
    timeout_seconds,
    resolved_address_hashes,
    allow_public_target,
):
    payload = {
        "run_id": run_id,
        "environment": environment,
        "target_url_sha256": target_url_sha256,
        "target_env_var": target_env_var,
        "runtime_env_vars": runtime_env_vars,
        "test_nodes": nodes,
        "generated_files": generated,
        "manifest_sha256": manifest_sha256,
        "python_executable_sha256": hashlib.sha256(
            os.path.realpath(sys.executable).encode("utf-8")
        ).hexdigest(),
        "python_version": list(sys.version_info[:3]),
        "timeout_seconds": timeout_seconds,
        "resolved_address_hashes": resolved_address_hashes,
        "allow_public_target": allow_public_target,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_pytest_runtime():
    if importlib.util.find_spec("pytest") is None:
        raise ExecutionError(
            "当前项目 runner 的 Python 环境无法导入 pytest，真实执行已阻断。"
        )


def _validate_http_transport_profile(profile):
    transport = profile.get("http_transport") if isinstance(profile, dict) else None
    if (
        not isinstance(transport, dict)
        or set(transport)
        != {
            "target_from_environment",
            "redirects_disabled",
            "status",
            "evidence",
        }
        or transport.get("status") != "confirmed"
        or transport.get("target_from_environment") is not True
        or transport.get("redirects_disabled") is not True
        or not isinstance(transport.get("evidence"), list)
        or not transport["evidence"]
    ):
        raise ExecutionError("项目画像未证明目标来自环境变量且自动重定向已关闭。")
    return transport


def execute(
    project_root,
    run_id,
    environment,
    target_url,
    confirmed_execution_digest,
    nodes,
    timeout_seconds,
    allow_public_target=False,
    preview=False,
):
    root = _check_root(project_root)
    _validate_project_python(root)
    expected_root_stat = os.stat(str(root), follow_symlinks=False)
    if not RUN_ID_PATTERN.fullmatch(run_id or ""):
        raise ExecutionError("run_id 格式无效。")
    if timeout_seconds <= 0 or timeout_seconds > 3600:
        raise ExecutionError("超时时间必须在 1 至 3600 秒之间。")
    safe_environment = _validate_environment(environment)
    _validate_pytest_runtime()
    target_host_sha256, target_url_sha256, normalized_target_url, resolved_addresses = (
        _validate_target_url(target_url, safe_environment, allow_public_target)
    )
    resolved_address_hashes = sorted(
        hashlib.sha256(str(address).encode("utf-8")).hexdigest()
        for address in resolved_addresses
    )
    root_fd = os.open(str(root), _directory_flags())
    run_fd = None
    try:
        opened_root_stat = os.fstat(root_fd)
        if (
            opened_root_stat.st_dev != expected_root_stat.st_dev
            or opened_root_stat.st_ino != expected_root_stat.st_ino
        ):
            raise ExecutionError("目标项目根目录在打开时发生替换。")
        manifest, generated, run_relative, manifest_sha256 = _load_manifest(
            root_fd, run_id
        )
        profile_bytes = _read_regular_at(
            root_fd,
            Path(".tide") / "project-profile.json",
            "项目画像",
            2 * 1024 * 1024,
        )
        profile_sha256 = hashlib.sha256(profile_bytes).hexdigest()
        if manifest.get("project_profile_sha256") != profile_sha256:
            raise ExecutionError("运行清单未绑定当前项目画像。")
        try:
            profile = json.loads(
                profile_bytes.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
            )
        except (UnicodeError, ValueError) as exc:
            raise ExecutionError("项目画像不是有效 JSON：%s" % exc)
        _validate_http_transport_profile(profile)
        runner = profile.get("pytest_runner") if isinstance(profile, dict) else None
        prefix = runner.get("argv_prefix") if isinstance(runner, dict) else None
        prefix_sha256 = hashlib.sha256(
            json.dumps(prefix, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        if (
            not isinstance(prefix, list)
            or not prefix
            or not isinstance(runner, dict)
            or runner.get("status") != "confirmed"
            or tuple(prefix) not in SAFE_RUNNER_PREFIXES
            or os.environ.get(RUNNER_PROFILE_ENV) != profile_sha256
            or os.environ.get(RUNNER_PREFIX_ENV) != prefix_sha256
        ):
            raise ExecutionError("执行器不是由项目画像已确认 runner 启动。")
        if str(manifest.get("environment", "")).strip().lower() != safe_environment:
            raise ExecutionError("执行环境与生成清单不一致。")
        validated_nodes = _validate_nodes(nodes, generated)
        target_env_var = manifest.get("target_env_var")
        if (
            not isinstance(target_env_var, str)
            or not ENV_NAME_PATTERN.fullmatch(target_env_var)
            or target_env_var.upper() in FORBIDDEN_ENV_NAMES
        ):
            raise ExecutionError("运行清单缺少有效的目标地址环境变量。")
        runtime_env_vars = _runtime_env_vars(manifest, target_env_var)
        execution_digest = _execution_digest(
            run_id,
            safe_environment,
            target_url_sha256,
            target_env_var,
            runtime_env_vars,
            validated_nodes,
            generated,
            manifest_sha256,
            timeout_seconds,
            resolved_address_hashes,
            allow_public_target,
        )
        if preview:
            return "NOT_RUN", None, execution_digest
        if confirmed_execution_digest != execution_digest:
            raise ExecutionError("确认摘要与当前执行计划不匹配。")
        _, current_url_sha256, _, current_addresses = _validate_target_url(
            target_url, safe_environment, allow_public_target
        )
        current_address_hashes = sorted(
            hashlib.sha256(str(address).encode("utf-8")).hexdigest()
            for address in current_addresses
        )
        if (
            current_url_sha256 != target_url_sha256
            or current_address_hashes != resolved_address_hashes
        ):
            raise ExecutionError("目标地址或 DNS 解析结果在确认后发生变化。")
        run_fd = _open_directory_path(root_fd, run_relative)
        for name in ("execution.json", "execution-report.md"):
            try:
                os.stat(name, dir_fd=run_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise ExecutionError("本次运行已经存在执行记录，拒绝覆盖或重复执行。")
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
        ] + validated_nodes
        started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        start = time.monotonic()
        timed_out = False
        return_code = None
        stdout_path = None
        stderr_path = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="tide-pytest-out-", delete=False
            ) as stdout_file:
                stdout_path = Path(stdout_file.name)
                with tempfile.NamedTemporaryFile(
                    prefix="tide-pytest-err-", delete=False
                ) as stderr_file:
                    stderr_path = Path(stderr_file.name)

                    def _enter_opened_root():
                        os.fchdir(root_fd)

                    try:
                        completed = subprocess.run(
                            command,
                            env=_safe_environment(
                                target_env_var,
                                normalized_target_url,
                                safe_environment,
                                runtime_env_vars,
                            ),
                            stdin=subprocess.DEVNULL,
                            stdout=stdout_file,
                            stderr=stderr_file,
                            timeout=timeout_seconds,
                            check=False,
                            shell=False,
                            pass_fds=(root_fd,),
                            preexec_fn=_enter_opened_root,
                        )
                        return_code = completed.returncode
                    except subprocess.TimeoutExpired:
                        timed_out = True
            stdout_sha256, stdout_bytes = _sha256_file(stdout_path)
            stderr_sha256, stderr_bytes = _sha256_file(stderr_path)
        finally:
            if stdout_path and stdout_path.exists():
                stdout_path.unlink()
            if stderr_path and stderr_path.exists():
                stderr_path.unlink()

        duration_seconds = round(time.monotonic() - start, 3)
        status = "BLOCKED" if timed_out else ("PASS" if return_code == 0 else "FAIL")
        record = {
            "format_version": 1,
            "run_id": run_id,
            "started_at": started_at,
            "environment": safe_environment,
            "target_host_sha256": target_host_sha256,
            "target_url_sha256": target_url_sha256,
            "resolved_address_hashes": resolved_address_hashes,
            "allow_public_target": allow_public_target,
            "target_env_var": target_env_var,
            "runtime_env_vars": runtime_env_vars,
            "execution_plan_digest": execution_digest,
            "test_nodes": validated_nodes,
            "command": [
                "<current-python>",
                "-m",
                "pytest",
                "-q",
                "-o",
                "addopts=",
                "-p",
                "no:cacheprovider",
            ]
            + validated_nodes,
            "execution_status": status,
            "return_code": return_code,
            "timed_out": timed_out,
            "duration_seconds": duration_seconds,
            "stdout": {"bytes": stdout_bytes, "sha256": stdout_sha256},
            "stderr": {"bytes": stderr_bytes, "sha256": stderr_sha256},
        }
        record_data = (
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        report_lines = [
            "# Tide 执行报告",
            "",
            "- 运行编号：`%s`" % run_id,
            "- 执行状态：`%s`" % status,
            "- 环境：`%s`" % safe_environment,
            "- 返回码：`%s`" % (return_code if return_code is not None else "未返回"),
            "- 耗时：`%s` 秒" % duration_seconds,
            "- 标准输出：仅记录大小 `%d` 与散列 `%s`" % (stdout_bytes, stdout_sha256),
            "- 标准错误：仅记录大小 `%d` 与散列 `%s`" % (stderr_bytes, stderr_sha256),
            "",
            "## 精确节点",
            "",
        ]
        report_lines.extend("- `%s`" % node for node in validated_nodes)
        report_data = ("\n".join(report_lines) + "\n").encode("utf-8")
        created = []
        try:
            _atomic_create_at(run_fd, "execution.json", record_data)
            created.append("execution.json")
            _atomic_create_at(run_fd, "execution-report.md", report_data)
            created.append("execution-report.md")
        except Exception:
            for name in reversed(created):
                try:
                    os.unlink(name, dir_fd=run_fd)
                except OSError:
                    pass
            raise
        return status, return_code, execution_digest
    finally:
        if run_fd is not None:
            try:
                os.close(run_fd)
            except OSError:
                pass
        os.close(root_fd)


def self_test():
    with tempfile.TemporaryDirectory(prefix="tide-python-binding-test-") as directory:
        root = Path(directory)
        (root / ".venv").mkdir()
        try:
            _validate_project_python(root)
        except ExecutionError:
            pass
        else:
            raise ExecutionError("自检未阻断宿主 Python 直接调用执行器。")
    original_find_spec = importlib.util.find_spec
    try:
        importlib.util.find_spec = lambda name: object()
        _validate_pytest_runtime()
        importlib.util.find_spec = lambda name: None
        try:
            _validate_pytest_runtime()
        except ExecutionError:
            pass
        else:
            raise ExecutionError("自检未能阻断缺少 pytest 的运行时。")
    finally:
        importlib.util.find_spec = original_find_spec
    if _validate_environment("test") != "test":
        raise ExecutionError("自检无法接受测试环境。")
    try:
        _validate_http_transport_profile(
            {
                "http_transport": {
                    "target_from_environment": False,
                    "redirects_disabled": False,
                    "status": "unknown",
                    "evidence": [],
                }
            }
        )
    except ExecutionError:
        pass
    else:
        raise ExecutionError("自检未阻断未经证实的 HTTP transport。")
    for blocked in ("", "unknown", "prod", "production"):
        try:
            _validate_environment(blocked)
        except ExecutionError:
            pass
        else:
            raise ExecutionError("自检未能阻断环境：%s" % blocked)
    target_hash, target_url_hash, normalized, addresses = _validate_target_url(
        "http://127.0.0.1", "local", False
    )
    if not HASH_PATTERN.fullmatch(target_hash):
        raise ExecutionError("自检无法生成目标主机散列。")
    if (
        not HASH_PATTERN.fullmatch(target_url_hash)
        or normalized != "http://127.0.0.1"
        or not addresses
    ):
        raise ExecutionError("自检无法绑定目标地址。")
    try:
        _validate_target_url("http://user:secret@127.0.0.1", "local", False)
    except ExecutionError:
        pass
    else:
        raise ExecutionError("自检未能阻断地址凭据。")
    variable_name = "TIDE_SELF_TEST_REQUIRED"
    unbound_name = "TIDE_SELF_TEST_UNBOUND"
    previous = os.environ.get(variable_name)
    previous_unbound = os.environ.get(unbound_name)
    try:
        os.environ[variable_name] = "self-test-value"
        os.environ[unbound_name] = "must-not-pass"
        names = _runtime_env_vars(
            {"runtime_env_vars": [variable_name]},
            "API_BASE_URL",
        )
        safe = _safe_environment(
            "API_BASE_URL", "https://sandbox.invalid", "test", names
        )
        if safe.get(variable_name) != "self-test-value":
            raise ExecutionError("自检未能透传已绑定的必需变量。")
        if unbound_name in safe:
            raise ExecutionError("自检错误透传了未绑定变量。")
        for forbidden in ("HOME", "PYTHONPATH", "VIRTUAL_ENV"):
            if forbidden in safe:
                raise ExecutionError(
                    "自检发现 pytest 环境透传了禁止变量：%s" % forbidden
                )
        os.environ[variable_name] = ""
        try:
            _runtime_env_vars({"runtime_env_vars": [variable_name]}, "API_BASE_URL")
        except ExecutionError:
            pass
        else:
            raise ExecutionError("自检未能阻断缺失的必需变量。")
    finally:
        if previous is None:
            os.environ.pop(variable_name, None)
        else:
            os.environ[variable_name] = previous
        if previous_unbound is None:
            os.environ.pop(unbound_name, None)
        else:
            os.environ[unbound_name] = previous_unbound


def build_parser():
    parser = argparse.ArgumentParser(
        description="在独立确认和安全环境门禁后执行精确 pytest 节点。"
    )
    parser.add_argument("--project-root", help="目标项目根目录")
    parser.add_argument("--run-id", help="已写入的 Tide 运行编号")
    parser.add_argument("--environment", help="用户确认的非生产环境")
    parser.add_argument("--target-url", help="用户确认的目标地址，仅记录主机散列")
    parser.add_argument(
        "--confirmed-execution-digest", help="用户确认的当前执行计划 SHA-256 摘要"
    )
    parser.add_argument(
        "--test-node",
        action="append",
        default=[],
        help="用户确认的精确 pytest 节点，可重复",
    )
    parser.add_argument(
        "--timeout-seconds", type=int, default=900, help="执行超时，范围 1 至 3600 秒"
    )
    parser.add_argument(
        "--allow-public-target",
        action="store_true",
        help="单独授权当前执行摘要绑定的公共网络目标",
    )
    parser.add_argument(
        "--preview", action="store_true", help="只校验并输出执行计划摘要，不启动 pytest"
    )
    parser.add_argument(
        "--self-test", action="store_true", help="运行内置安全门禁自检后退出"
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print("run_pytest.py 自检通过。")
            return 0
        required = (args.project_root, args.run_id, args.environment, args.target_url)
        if not all(required):
            raise ExecutionError("必须提供项目、运行、环境和目标参数。")
        if not args.preview and not args.confirmed_execution_digest:
            raise ExecutionError("实际执行必须提供 --confirmed-execution-digest。")
        status, return_code, execution_digest = execute(
            Path(args.project_root),
            args.run_id,
            args.environment,
            args.target_url,
            args.confirmed_execution_digest,
            args.test_node,
            args.timeout_seconds,
            allow_public_target=args.allow_public_target,
            preview=args.preview,
        )
        if args.preview:
            print("执行计划预检通过；执行摘要：%s。" % execution_digest)
            return 0
        print("pytest 执行结束：%s。" % status)
        return 0 if status == "PASS" else (1 if status == "FAIL" else 2)
    except ExecutionError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
