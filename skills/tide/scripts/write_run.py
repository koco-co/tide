#!/usr/bin/env python3
"""校验写入计划，只新增测试文件和脱敏运行记录。"""

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from candidate_checks import CandidateCheckError, validate_candidate

MAX_PLAN_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
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
GENERATION_ONLY_ENVIRONMENTS = {"unknown", "prod", "production"}
SAFE_RUNNERS = {
    ("uv", "run", "--locked", "--no-sync", "python"): "uv.lock",
    ("poetry", "run", "python"): "poetry.lock",
    ("pipenv", "run", "python"): "Pipfile.lock",
    ("pdm", "run", "python"): "pdm.lock",
}


class WritePlanError(Exception):
    pass


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _plan_digest(plan):
    encoded = json.dumps(
        plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256(encoded)


def _new_run_id():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%Sz").lower()
    return "tide-%s-%s" % (timestamp, secrets.token_hex(4))


def _reject_duplicate_keys(pairs):
    value = {}
    for key, child in pairs:
        if key in value:
            raise WritePlanError("JSON 包含重复字段：%s" % key)
        value[key] = child
    return value


def _is_within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _check_regular_file(path, label, max_bytes):
    try:
        info = os.lstat(str(path))
    except OSError as exc:
        raise WritePlanError("无法读取%s：%s" % (label, exc))
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
    ):
        raise WritePlanError("%s必须是普通文件，不能是软链接。" % label)
    if info.st_size > max_bytes:
        raise WritePlanError("%s超过大小限制。" % label)


def _check_root(root):
    try:
        info = os.lstat(str(root))
    except OSError as exc:
        raise WritePlanError("目标项目根目录不可用：%s" % exc)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise WritePlanError("目标项目根目录必须是真实目录，不能是软链接。")
    return root.resolve()


def _root_identity(root):
    info = os.stat(str(root), follow_symlinks=False)
    return {
        "resolved_path_sha256": _sha256(str(root).encode("utf-8")),
        "device": info.st_dev,
        "inode": info.st_ino,
    }


def _relative_path(value, label):
    path = Path(str(value))
    if (
        path.is_absolute()
        or not path.parts
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise WritePlanError("%s必须是规范的项目内相对路径。" % label)
    return path


def _check_existing_path_no_symlink(root, path, require_directory=False):
    current = root
    for part in path.parts:
        current = current / part
        try:
            info = os.lstat(str(current))
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise WritePlanError("检查路径失败：%s" % exc)
        if stat.S_ISLNK(info.st_mode):
            raise WritePlanError("路径包含软链接：%s" % path)
    if require_directory and not current.is_dir():
        raise WritePlanError("确认的测试目录不是目录：%s" % path)
    return True


def _load_plan(plan_path):
    _check_regular_file(plan_path, "写入计划", MAX_PLAN_BYTES)
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not _is_within(plan_path.resolve(), temp_root):
        raise WritePlanError("写入计划只能位于系统临时目录。")
    descriptor = None
    try:
        descriptor = os.open(str(plan_path), os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "r", encoding="utf-8", closefd=False) as handle:
            plan = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, ValueError) as exc:
        raise WritePlanError("写入计划不是有效 JSON：%s" % exc)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return _load_plan_value(plan)


def _load_plan_value(plan):
    if not isinstance(plan, dict):
        raise WritePlanError("写入计划顶层必须是对象。")
    expected = {
        "run_id",
        "environment",
        "scenario_ids",
        "target_env_var",
        "runtime_env_vars",
        "source_summary_sha256",
        "scenario_plan_sha256",
        "project_profile_sha256",
        "project_rules_sha256",
        "generation_status",
        "files",
    }
    if set(plan) != expected:
        raise WritePlanError("写入计划字段不完整或包含未知字段。")
    if not isinstance(plan["run_id"], str) or not RUN_ID_PATTERN.fullmatch(
        plan["run_id"]
    ):
        raise WritePlanError("run_id 必须使用 tide- 前缀和安全字符。")
    if not isinstance(plan["environment"], str):
        raise WritePlanError("environment 必须是字符串。")
    environment = plan["environment"].strip().lower()
    if environment not in SAFE_ENVIRONMENTS | GENERATION_ONLY_ENVIRONMENTS:
        raise WritePlanError("environment 必须使用脚本支持的精确环境名。")
    plan["environment"] = environment
    scenario_ids = plan["scenario_ids"]
    if (
        not isinstance(scenario_ids, list)
        or not scenario_ids
        or any(not isinstance(item, str) or not item for item in scenario_ids)
        or len(set(scenario_ids)) != len(scenario_ids)
    ):
        raise WritePlanError("scenario_ids 必须是唯一非空字符串数组。")
    target_env_var = plan["target_env_var"]
    if (
        not isinstance(target_env_var, str)
        or not ENV_NAME_PATTERN.fullmatch(target_env_var)
        or target_env_var.upper() in FORBIDDEN_ENV_NAMES
    ):
        raise WritePlanError("target_env_var 必须是项目已确认的安全环境变量名。")
    runtime_env_vars = plan["runtime_env_vars"]
    if not isinstance(runtime_env_vars, list) or len(runtime_env_vars) > 32:
        raise WritePlanError("runtime_env_vars 必须是最多三十二项的字符串数组。")
    seen_runtime_env_vars = set()
    for index, name in enumerate(runtime_env_vars):
        if (
            not isinstance(name, str)
            or not ENV_NAME_PATTERN.fullmatch(name)
            or name.upper() in FORBIDDEN_ENV_NAMES
            or name.upper() == target_env_var.upper()
            or name in seen_runtime_env_vars
        ):
            raise WritePlanError(
                "runtime_env_vars[%d] 不是唯一、安全的非目标环境变量名。" % index
            )
        seen_runtime_env_vars.add(name)
    for field in (
        "source_summary_sha256",
        "scenario_plan_sha256",
        "project_profile_sha256",
        "project_rules_sha256",
    ):
        if not isinstance(plan[field], str) or not HASH_PATTERN.fullmatch(plan[field]):
            raise WritePlanError("%s 必须是六十四位小写十六进制散列。" % field)
    if plan["generation_status"] not in ("PASS", "PARTIAL"):
        raise WritePlanError("generation_status 只能是 PASS 或 PARTIAL。")
    if not isinstance(plan["files"], list) or not plan["files"]:
        raise WritePlanError("files 必须是非空数组。")
    return plan


def _load_candidate(candidate_path):
    _check_regular_file(candidate_path, "生成候选", MAX_PLAN_BYTES)
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not _is_within(candidate_path.resolve(), temp_root):
        raise WritePlanError("生成候选只能位于系统临时目录。")
    try:
        with candidate_path.open("r", encoding="utf-8") as handle:
            candidate = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, ValueError) as exc:
        raise WritePlanError("生成候选不是有效 JSON：%s" % exc)
    expected = {
        "scenario_ids",
        "files",
    }
    if not isinstance(candidate, dict) or set(candidate) != expected:
        raise WritePlanError("生成候选字段不完整或包含未知字段。")
    return candidate


def _load_scenario_plan(path, confirmed_digest, profile_digest, rules_digest):
    _check_regular_file(path, "场景计划", MAX_PLAN_BYTES)
    if not _is_within(path.resolve(), Path(tempfile.gettempdir()).resolve()):
        raise WritePlanError("场景计划只能位于系统临时目录。")
    raw = path.read_bytes()
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeError, ValueError) as exc:
        raise WritePlanError("场景计划不是有效 JSON：%s" % exc)
    expected = {
        "schema_version",
        "kind",
        "source_summary_sha256",
        "project_profile_sha256",
        "project_rules_sha256",
        "analysis",
        "analysis_sha256",
        "confirmation_summary",
        "plan_digest",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise WritePlanError("场景计划字段不完整或包含未知字段。")
    without_digest = dict(value)
    plan_digest = without_digest.pop("plan_digest")
    if (
        value["schema_version"] != "1.0"
        or value["kind"] != "tide-scenarios"
        or not isinstance(plan_digest, str)
        or plan_digest
        != _sha256(
            json.dumps(
                without_digest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        or confirmed_digest != plan_digest
    ):
        raise WritePlanError("场景计划摘要无效或未经当前确认。")
    if (
        value["project_profile_sha256"] != profile_digest
        or value["project_rules_sha256"] != rules_digest
    ):
        raise WritePlanError("场景计划未绑定当前项目画像与规则。")
    if not isinstance(
        value["source_summary_sha256"], str
    ) or not HASH_PATTERN.fullmatch(value["source_summary_sha256"]):
        raise WritePlanError("场景计划缺少有效脱敏摘要散列。")
    if not isinstance(value["analysis"], dict) or value["analysis_sha256"] != _sha256(
        json.dumps(
            value["analysis"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ):
        raise WritePlanError("场景计划分析内容摘要无效。")
    confirmation = value["confirmation_summary"]
    if not isinstance(confirmation, dict) or set(confirmation) != {
        "status",
        "scenario_ids",
        "referenced_entry_ids",
        "questions",
        "excluded",
    }:
        raise WritePlanError("场景确认摘要字段无效。")
    scenario_ids = confirmation["scenario_ids"]
    if (
        not isinstance(scenario_ids, list)
        or not scenario_ids
        or any(not isinstance(item, str) for item in scenario_ids)
    ):
        raise WritePlanError("场景确认摘要缺少场景编号。")
    return value, _sha256(raw), scenario_ids


def _load_profile(root):
    path = root / ".tide" / "project-profile.json"
    _check_regular_file(path, "项目画像", MAX_PLAN_BYTES)
    try:
        with path.open("r", encoding="utf-8") as handle:
            profile = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, ValueError) as exc:
        raise WritePlanError("项目画像不是有效 JSON：%s" % exc)
    if not isinstance(profile, dict):
        raise WritePlanError("项目画像顶层必须是对象。")
    return profile


def _confirmed_profile_variables(profile):
    variables = profile.get("runtime_environment_variables")
    if not isinstance(variables, list):
        raise WritePlanError("项目画像缺少有效的运行时环境变量清单。")
    confirmed = {}
    for index, item in enumerate(variables):
        if not isinstance(item, dict):
            raise WritePlanError("项目画像运行时环境变量第 %d 项无效。" % index)
        name = item.get("name")
        if (
            not isinstance(name, str)
            or not ENV_NAME_PATTERN.fullmatch(name)
            or item.get("status") != "confirmed"
            or name in confirmed
        ):
            raise WritePlanError("项目画像包含未确认、重复或无效的环境变量。")
        confirmed[name] = item
    return confirmed


def _profile_runtime_bindings(profile):
    confirmed = _confirmed_profile_variables(profile)
    targets = [
        name
        for name, item in confirmed.items()
        if item.get("role") == "target_url" and item.get("required") is True
    ]
    if len(targets) != 1:
        raise WritePlanError("项目画像必须恰好包含一个已确认的必需目标地址变量。")
    runtime = [
        name
        for name, item in confirmed.items()
        if item.get("role") != "target_url" and item.get("required") is True
    ]
    return targets[0], runtime


def _validate_plan_profile_binding(plan, profile):
    confirmed = _confirmed_profile_variables(profile)
    target = confirmed.get(plan["target_env_var"])
    if (
        target is None
        or target.get("role") != "target_url"
        or target.get("required") is not True
    ):
        raise WritePlanError(
            "target_env_var 未绑定项目画像中已确认的必需目标地址变量。"
        )
    for name in plan["runtime_env_vars"]:
        item = confirmed.get(name)
        if (
            item is None
            or item.get("role") == "target_url"
            or item.get("required") is not True
        ):
            raise WritePlanError(
                "runtime_env_vars 包含画像未确认或非必需的变量：%s" % name
            )


def _project_evidence_digests(root):
    root_fd = os.open(str(root), _directory_flags())
    try:
        profile_digest = _file_digest_at(
            root_fd, Path(".tide") / "project-profile.json"
        )
        rules_fd = _open_directory_path(root_fd, Path(".tide") / "rules")
        try:
            entries = _rules_entries_at(rules_fd)
        finally:
            os.close(rules_fd)
    finally:
        os.close(root_fd)
    rules_digest = _sha256(
        json.dumps(
            entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )
    return profile_digest, rules_digest


def _write_new_json(path, value, label):
    temp_root = Path(tempfile.gettempdir()).resolve()
    parent = path.parent.resolve(strict=True)
    if not _is_within(parent, temp_root):
        raise WritePlanError("%s只能写入系统临时目录。" % label)
    if path.exists() or path.is_symlink():
        raise WritePlanError("拒绝覆盖既有%s。" % label)
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    parent_fd = os.open(str(parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptor = None
    try:
        descriptor = os.open(
            path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(parent_fd)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)


def bind_candidate(
    project_root,
    candidate_path,
    scenario_path,
    confirmed_scenario_digest,
    environment,
    output_path,
):
    root = _check_root(project_root)
    candidate = _load_candidate(candidate_path)
    profile = _load_profile(root)
    target_env_var, runtime_env_vars = _profile_runtime_bindings(profile)
    profile_digest, rules_digest = _project_evidence_digests(root)
    scenario_plan, scenario_plan_sha256, confirmed_scenario_ids = _load_scenario_plan(
        scenario_path,
        confirmed_scenario_digest,
        profile_digest,
        rules_digest,
    )
    candidate_scenario_ids = candidate["scenario_ids"]
    if (
        not isinstance(candidate_scenario_ids, list)
        or not candidate_scenario_ids
        or any(not isinstance(item, str) for item in candidate_scenario_ids)
        or len(set(candidate_scenario_ids)) != len(candidate_scenario_ids)
        or not set(candidate_scenario_ids).issubset(set(confirmed_scenario_ids))
    ):
        raise WritePlanError("生成候选场景编号未绑定已确认场景。")
    generation_status = (
        "PASS"
        if set(candidate_scenario_ids) == set(confirmed_scenario_ids)
        else "PARTIAL"
    )
    plan = {
        "run_id": _new_run_id(),
        "environment": environment,
        "scenario_ids": candidate_scenario_ids,
        "target_env_var": target_env_var,
        "runtime_env_vars": runtime_env_vars,
        "source_summary_sha256": scenario_plan["source_summary_sha256"],
        "scenario_plan_sha256": scenario_plan_sha256,
        "project_profile_sha256": profile_digest,
        "project_rules_sha256": rules_digest,
        "generation_status": generation_status,
        "files": candidate["files"],
    }
    plan = _load_plan_value(plan)
    _validate_plan_profile_binding(plan, profile)
    _write_new_json(output_path, plan, "写入计划")
    return plan


def _candidate_validation_digest(root, plan, test_dirs, status):
    config = _ruff_configuration(root)
    config_binding = None
    if config is not None:
        config_binding = {
            "relative_path": config.relative_to(root).as_posix(),
            "sha256": _sha256(config.read_bytes()),
        }
    payload = {
        "plan_sha256": _plan_digest(plan),
        "target_root_identity": _root_identity(root),
        "confirmed_test_dirs": [
            _relative_path(value, "测试目录").as_posix() for value in test_dirs
        ],
        "ruff_configuration": config_binding,
        "status": status,
    }
    return _sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def bind_review(project_root, plan_path, review_candidate_path, test_dirs, output_path):
    root = _check_root(project_root)
    plan = _load_plan(plan_path)
    _check_regular_file(review_candidate_path, "审查候选", MAX_PLAN_BYTES)
    if not _is_within(
        review_candidate_path.resolve(), Path(tempfile.gettempdir()).resolve()
    ):
        raise WritePlanError("审查候选只能位于系统临时目录。")
    try:
        with review_candidate_path.open("r", encoding="utf-8") as handle:
            candidate = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, ValueError) as exc:
        raise WritePlanError("审查候选不是有效 JSON：%s" % exc)
    expected = {
        "schema_version",
        "verdict",
        "blocking_findings",
        "non_blocking_findings",
        "information_gaps",
    }
    if not isinstance(candidate, dict) or set(candidate) != expected:
        raise WritePlanError("审查候选字段不完整或包含未知字段。")
    if candidate["schema_version"] != "1.0":
        raise WritePlanError("审查候选 schema_version 无效。")
    for field in ("blocking_findings", "non_blocking_findings", "information_gaps"):
        if not isinstance(candidate[field], list):
            raise WritePlanError("审查候选字段必须是数组：%s" % field)
    if candidate["verdict"] != "PASS" or candidate["blocking_findings"]:
        raise WritePlanError("审查候选尚未通过，不得绑定写入计划。")
    validation_status, _ = validate_candidates(root, plan_path, test_dirs)
    review = {
        "schema_version": "1.0",
        "verdict": "PASS",
        "reviewed_plan_sha256": _plan_digest(plan),
        "candidate_validation_sha256": _candidate_validation_digest(
            root, plan, test_dirs, validation_status
        ),
        "blocking_findings": [],
        "non_blocking_findings": candidate["non_blocking_findings"],
        "verified_scope": [item["relative_path"] for item in plan["files"]],
        "information_gaps": candidate["information_gaps"],
    }
    _write_new_json(output_path, review, "绑定审查结果")
    return review


def _load_review(review_path, plan_digest, candidate_validation_digest, expected_scope):
    _check_regular_file(review_path, "审查结果", MAX_PLAN_BYTES)
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not _is_within(review_path.resolve(), temp_root):
        raise WritePlanError("审查结果只能位于系统临时目录。")
    descriptor = None
    try:
        descriptor = os.open(str(review_path), os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "r", encoding="utf-8", closefd=False) as handle:
            review = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, ValueError) as exc:
        raise WritePlanError("审查结果不是有效 JSON：%s" % exc)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    expected = {
        "schema_version",
        "verdict",
        "reviewed_plan_sha256",
        "candidate_validation_sha256",
        "blocking_findings",
        "non_blocking_findings",
        "verified_scope",
        "information_gaps",
    }
    if not isinstance(review, dict) or set(review) != expected:
        raise WritePlanError("审查结果字段不完整或包含未知字段。")
    if review["schema_version"] != "1.0" or review["verdict"] != "PASS":
        raise WritePlanError("审查结果尚未通过。")
    if review["reviewed_plan_sha256"] != plan_digest:
        raise WritePlanError("审查结果未绑定当前写入计划。")
    if review["candidate_validation_sha256"] != candidate_validation_digest:
        raise WritePlanError("审查结果未绑定当前候选机械校验。")
    for field in (
        "blocking_findings",
        "non_blocking_findings",
        "verified_scope",
        "information_gaps",
    ):
        if not isinstance(review[field], list):
            raise WritePlanError("审查结果字段必须是数组：%s" % field)
    if review["blocking_findings"]:
        raise WritePlanError("审查结果仍有阻塞问题。")
    if set(review["verified_scope"]) != set(expected_scope) or len(
        review["verified_scope"]
    ) != len(expected_scope):
        raise WritePlanError("审查结果未逐项覆盖当前计划的全部文件。")
    return review, _sha256(
        json.dumps(
            review, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def _prepare(root, plan, test_dirs, profile=None):
    tide_dir = Path(".tide")
    if not _check_existing_path_no_symlink(root, tide_dir, require_directory=True):
        raise WritePlanError("目标项目尚未初始化：缺少 .tide 目录。")
    normalized_test_dirs = []
    for value in test_dirs:
        relative = _relative_path(value, "测试目录")
        if relative == tide_dir or _is_within(relative, tide_dir):
            raise WritePlanError("测试目录不能位于 .tide 中。")
        if not _check_existing_path_no_symlink(root, relative, require_directory=True):
            raise WritePlanError("确认的测试目录不存在：%s" % relative)
        normalized_test_dirs.append(relative)
    if not normalized_test_dirs:
        raise WritePlanError("至少需要一个用户确认的现有测试目录。")

    prepared = []
    seen = set()
    for index, item in enumerate(plan["files"]):
        if not isinstance(item, dict) or set(item) != {"relative_path", "content"}:
            raise WritePlanError("files[%d] 字段无效。" % index)
        relative = _relative_path(item["relative_path"], "测试文件路径")
        if relative.suffix != ".py":
            raise WritePlanError("测试文件必须使用 .py 扩展名：%s" % relative)
        if not any(
            relative != test_dir and _is_within(relative, test_dir)
            for test_dir in normalized_test_dirs
        ):
            raise WritePlanError("测试文件越过用户确认目录：%s" % relative)
        if str(relative) in seen:
            raise WritePlanError("写入计划包含重复路径：%s" % relative)
        seen.add(str(relative))
        content = item["content"]
        if not isinstance(content, str) or "\x00" in content:
            raise WritePlanError("测试文件内容必须是无空字节的字符串：%s" % relative)
        if profile is not None:
            try:
                validate_candidate(root, profile, content, relative)
            except CandidateCheckError as exc:
                raise WritePlanError(str(exc))
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_FILE_BYTES:
            raise WritePlanError("测试文件超过大小限制：%s" % relative)
        target = root / relative
        _check_existing_path_no_symlink(root, relative.parent)
        if target.exists() or target.is_symlink():
            raise WritePlanError("目标文件已存在，拒绝覆盖：%s" % relative)
        prepared.append((relative, encoded, _sha256(encoded)))

    run_relative = Path(".tide") / "runs" / plan["run_id"]
    run_target = root / run_relative
    _check_existing_path_no_symlink(root, run_relative.parent)
    if run_target.exists() or run_target.is_symlink():
        raise WritePlanError("运行目录已存在，拒绝覆盖：%s" % run_relative)
    return prepared, run_relative, normalized_test_dirs


def _ruff_configuration(root):
    candidates = [root / "pyproject.toml", root / "ruff.toml", root / ".ruff.toml"]
    for path in candidates:
        try:
            info = os.lstat(str(path))
        except FileNotFoundError:
            continue
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
        ):
            raise WritePlanError("Ruff 配置必须是唯一普通文件：%s" % path.name)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if path.name != "pyproject.toml" or "[tool.ruff" in text:
            return path
    return None


def _isolated_tool_environment(temporary_root):
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
    cache_root = Path(temporary_root) / "tool-cache"
    uv_cache = cache_root / "uv"
    xdg_cache = cache_root / "xdg"
    uv_cache.mkdir(parents=True, exist_ok=False)
    xdg_cache.mkdir(parents=True, exist_ok=False)
    environment["UV_CACHE_DIR"] = str(uv_cache)
    environment["XDG_CACHE_HOME"] = str(xdg_cache)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _require_prepared_runner(root, prefix):
    environment_dir = root / ".venv"
    try:
        environment_info = os.lstat(str(environment_dir))
    except FileNotFoundError:
        raise WritePlanError(
            "项目 runner 环境尚未准备；为避免自动创建 .venv，Tide 未启动 Ruff。"
        )
    if stat.S_ISLNK(environment_info.st_mode) or not stat.S_ISDIR(
        environment_info.st_mode
    ):
        raise WritePlanError("项目 .venv 必须是现有真实目录，不能是软链接。")
    configuration = environment_dir / "pyvenv.cfg"
    executables = (
        environment_dir / "bin" / "python",
        environment_dir / "Scripts" / "python.exe",
    )
    try:
        configuration_info = os.lstat(str(configuration))
    except OSError:
        configuration_info = None
    if (
        configuration_info is None
        or stat.S_ISLNK(configuration_info.st_mode)
        or not stat.S_ISREG(configuration_info.st_mode)
        or configuration_info.st_nlink != 1
        or not any(path.exists() and path.resolve().is_file() for path in executables)
    ):
        raise WritePlanError("项目 .venv 不完整，拒绝由 Tide 自动创建或修复。")


def _project_python(root):
    executables = (
        root / ".venv" / "bin" / "python",
        root / ".venv" / "Scripts" / "python.exe",
    )
    for executable in executables:
        try:
            resolved = executable.resolve(strict=True)
        except OSError:
            continue
        if resolved.is_file():
            return executable
    raise WritePlanError("项目 .venv 缺少可用 Python。")


def validate_candidates(project_root, plan_path, test_dirs):
    root = _check_root(project_root)
    plan = _load_plan(plan_path)
    profile = _load_profile(root)
    _validate_plan_profile_binding(plan, profile)
    prepared, _, _ = _prepare(root, plan, test_dirs, profile)
    _verify_project_evidence(root, plan)
    config = _ruff_configuration(root)
    runner = profile.get("pytest_runner")
    if config is None:
        return "SKIPPED", "项目没有 Ruff 配置，未声明的静态检查不自动补装"
    if not isinstance(runner, dict) or runner.get("status") != "confirmed":
        raise WritePlanError("项目存在 Ruff 配置，但画像没有已确认 runner。")
    prefix = runner.get("argv_prefix")
    if not isinstance(prefix, list):
        raise WritePlanError("项目存在 Ruff 配置，但画像 runner 结构无效。")
    lock_name = SAFE_RUNNERS.get(tuple(prefix))
    if lock_name is None:
        raise WritePlanError("项目画像 runner 不在 Tide 安全白名单中。")
    lock_path = root / lock_name
    try:
        lock_info = os.lstat(str(lock_path))
    except OSError:
        lock_info = None
    if (
        lock_info is None
        or stat.S_ISLNK(lock_info.st_mode)
        or not stat.S_ISREG(lock_info.st_mode)
        or lock_info.st_nlink != 1
    ):
        raise WritePlanError("项目画像 runner 缺少对应普通锁文件：%s" % lock_name)
    _require_prepared_runner(root, prefix)
    with tempfile.TemporaryDirectory(prefix="tide-candidate-check-") as directory:
        temporary_root = Path(directory)
        candidate_paths = []
        for index, (relative, encoded, _) in enumerate(prepared):
            candidate = temporary_root / ("%03d-%s" % (index, relative.name))
            candidate.write_bytes(encoded)
            candidate_paths.append(str(candidate))
        command = (
            [str(_project_python(root))]
            + [
                "-m",
                "ruff",
                "check",
                "--no-cache",
                "--config",
                str(config),
            ]
            + candidate_paths
        )
        completed = subprocess.run(
            command,
            cwd=str(root),
            env=_isolated_tool_environment(temporary_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )
    diagnostics = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0:
        raise WritePlanError(
            "候选未通过项目 Ruff 检查（退出码 %d）：%s"
            % (completed.returncode, diagnostics[:4000])
        )
    return "PASS", diagnostics or "Ruff 检查通过"


def _directory_flags():
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise WritePlanError("当前系统不支持安全目录文件描述符操作。")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _open_directory_path(root_fd, relative, create=False, created_dirs=None):
    current_fd = os.dup(root_fd)
    traversed = Path()
    try:
        for part in relative.parts:
            traversed = traversed / part
            try:
                next_fd = os.open(part, _directory_flags(), dir_fd=current_fd)
            except FileNotFoundError:
                if not create:
                    raise WritePlanError("目录不存在：%s" % traversed)
                os.mkdir(part, 0o755, dir_fd=current_fd)
                if created_dirs is not None:
                    created_dirs.append(traversed)
                next_fd = os.open(part, _directory_flags(), dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _atomic_create_at(parent_fd, name, data):
    temporary_name = ".tide-write-%s" % secrets.token_hex(12)
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
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_name is not None:
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass


def _file_digest_at(root_fd, relative):
    parent_fd = _open_directory_path(root_fd, relative.parent)
    descriptor = None
    try:
        descriptor = os.open(
            relative.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd
        )
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise WritePlanError("目标不是普通文件：%s" % relative)
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)


def _rules_entries_at(directory_fd, prefix=Path()):
    entries = []
    for name in sorted(os.listdir(directory_fd)):
        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        relative = prefix / name
        if stat.S_ISDIR(info.st_mode):
            child_fd = os.open(name, _directory_flags(), dir_fd=directory_fd)
            try:
                entries.extend(_rules_entries_at(child_fd, relative))
            finally:
                os.close(child_fd)
            continue
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or relative.suffix.lower() != ".md"
            or name.startswith(".")
        ):
            raise WritePlanError("项目规则目录包含非 Markdown 普通文件：%s" % relative)
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        try:
            digest = hashlib.sha256()
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        finally:
            os.close(descriptor)
        entries.append({"path": relative.as_posix(), "sha256": digest.hexdigest()})
    return entries


def _verify_project_evidence_at(root_fd, plan):
    profile_digest = _file_digest_at(root_fd, Path(".tide") / "project-profile.json")
    rules_fd = _open_directory_path(root_fd, Path(".tide") / "rules")
    try:
        entries = _rules_entries_at(rules_fd)
    finally:
        os.close(rules_fd)
    rules_digest = _sha256(
        json.dumps(
            entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )
    if profile_digest != plan["project_profile_sha256"]:
        raise WritePlanError("当前项目画像与写入计划绑定散列不一致。")
    if rules_digest != plan["project_rules_sha256"]:
        raise WritePlanError("当前项目规则与写入计划绑定散列不一致。")


def _verify_project_evidence(root, plan):
    root_fd = os.open(str(root), _directory_flags())
    try:
        _verify_project_evidence_at(root_fd, plan)
    finally:
        os.close(root_fd)


def _rollback_at(root_fd, created_files, created_dirs):
    for relative, digest in reversed(created_files):
        try:
            if _file_digest_at(root_fd, relative) != digest:
                continue
            parent_fd = _open_directory_path(root_fd, relative.parent)
            try:
                os.unlink(relative.name, dir_fd=parent_fd)
            finally:
                os.close(parent_fd)
        except (FileNotFoundError, OSError, WritePlanError):
            pass
    for relative in reversed(created_dirs):
        try:
            parent_fd = _open_directory_path(root_fd, relative.parent)
            try:
                os.rmdir(relative.name, dir_fd=parent_fd)
            finally:
                os.close(parent_fd)
        except (FileNotFoundError, OSError, WritePlanError):
            pass


def _write_authorization_digest(plan_digest, review_digest, root_identity, test_dirs):
    payload = {
        "plan_sha256": plan_digest,
        "review_sha256": review_digest,
        "target_root_identity": root_identity,
        "confirmed_test_dirs": [path.as_posix() for path in test_dirs],
    }
    return _sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def execute(
    project_root,
    plan_path,
    review_path,
    test_dirs,
    confirmed_write_digest=None,
    preflight=False,
):
    root = _check_root(project_root)
    expected_root_identity = _root_identity(root)
    plan = _load_plan(plan_path)
    profile = _load_profile(root)
    _validate_plan_profile_binding(plan, profile)
    prepared, run_relative, normalized_test_dirs = _prepare(
        root, plan, test_dirs, profile
    )
    plan_digest = _plan_digest(plan)
    validation_status, _ = validate_candidates(root, plan_path, test_dirs)
    candidate_validation_digest = _candidate_validation_digest(
        root, plan, test_dirs, validation_status
    )
    _, review_digest = _load_review(
        review_path,
        plan_digest,
        candidate_validation_digest,
        [relative.as_posix() for relative, _, _ in prepared],
    )
    write_digest = _write_authorization_digest(
        plan_digest,
        review_digest,
        expected_root_identity,
        normalized_test_dirs,
    )
    verification_fd = os.open(str(root), _directory_flags())
    try:
        _verify_project_evidence_at(verification_fd, plan)
    finally:
        os.close(verification_fd)
    if preflight:
        return plan["run_id"], len(prepared), write_digest
    if confirmed_write_digest != write_digest:
        raise WritePlanError("确认摘要与当前写入授权不匹配。")

    created_files = []
    created_dirs = []
    root_fd = os.open(str(root), _directory_flags())
    root_stat = os.fstat(root_fd)
    try:
        opened_identity = {
            "resolved_path_sha256": _sha256(str(root).encode("utf-8")),
            "device": root_stat.st_dev,
            "inode": root_stat.st_ino,
        }
        if opened_identity != expected_root_identity:
            raise WritePlanError("目标项目根目录在打开时发生替换。")
        _verify_project_evidence_at(root_fd, plan)
        run_fd = _open_directory_path(
            root_fd, run_relative, create=True, created_dirs=created_dirs
        )
        os.close(run_fd)
        for relative, content, digest in prepared:
            parent_fd = _open_directory_path(
                root_fd, relative.parent, create=True, created_dirs=created_dirs
            )
            try:
                _atomic_create_at(parent_fd, relative.name, content)
            finally:
                os.close(parent_fd)
            created_files.append((relative, digest))

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        manifest = {
            "format_version": 1,
            "run_id": plan["run_id"],
            "created_at": now,
            "environment": plan["environment"],
            "scenario_ids": plan["scenario_ids"],
            "target_env_var": plan["target_env_var"],
            "runtime_env_vars": plan["runtime_env_vars"],
            "source_summary_sha256": plan["source_summary_sha256"],
            "scenario_plan_sha256": plan["scenario_plan_sha256"],
            "project_profile_sha256": plan["project_profile_sha256"],
            "project_rules_sha256": plan["project_rules_sha256"],
            "write_plan_sha256": plan_digest,
            "generation_review_sha256": review_digest,
            "write_authorization_sha256": write_digest,
            "generation_status": plan["generation_status"],
            "execution_status": "NOT_RUN",
            "files": [
                {"relative_path": str(relative), "sha256": digest}
                for relative, _, digest in prepared
            ],
        }
        manifest_data = (
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        run_fd = _open_directory_path(root_fd, run_relative)
        try:
            _atomic_create_at(run_fd, "manifest.json", manifest_data)
        finally:
            os.close(run_fd)
        created_files.append((run_relative / "manifest.json", _sha256(manifest_data)))

        report_lines = [
            "# Tide 生成报告",
            "",
            "- 运行编号：`%s`" % plan["run_id"],
            "- 生成状态：`%s`" % plan["generation_status"],
            "- 执行状态：`NOT_RUN`",
            "- 脱敏摘要散列：`%s`" % plan["source_summary_sha256"],
            "",
            "## 新建文件",
            "",
        ]
        for relative, _, digest in prepared:
            report_lines.append("- `%s`：`%s`" % (relative, digest))
        report_data = ("\n".join(report_lines) + "\n").encode("utf-8")
        run_fd = _open_directory_path(root_fd, run_relative)
        try:
            _atomic_create_at(run_fd, "report.md", report_data)
        finally:
            os.close(run_fd)
        created_files.append((run_relative / "report.md", _sha256(report_data)))
        current_root = root.stat()
        if (
            current_root.st_dev != root_stat.st_dev
            or current_root.st_ino != root_stat.st_ino
        ):
            raise WritePlanError("目标项目根目录在写入期间发生替换。")
    except Exception:
        _rollback_at(root_fd, created_files, created_dirs)
        raise
    finally:
        os.close(root_fd)
    return plan["run_id"], len(prepared), write_digest


def self_test():
    from bind_scenarios import bind as bind_scenario_plan
    from sanitize_har import DEFAULT_MAX_BYTES, DEFAULT_MAX_ENTRIES, sanitize

    with tempfile.TemporaryDirectory(prefix="tide-write-test-") as directory:
        unbound_name = "TIDE_SELF_TEST_UNBOUND_SECRET"
        previous_unbound = os.environ.get(unbound_name)
        try:
            os.environ[unbound_name] = "must-not-pass"
            tool_environment = _isolated_tool_environment(
                Path(directory) / "isolated-environment"
            )
        finally:
            if previous_unbound is None:
                os.environ.pop(unbound_name, None)
            else:
                os.environ[unbound_name] = previous_unbound
        cache_root = (Path(directory) / "isolated-environment").resolve()
        for name in ("UV_CACHE_DIR", "XDG_CACHE_HOME"):
            cache_path = Path(tool_environment[name]).resolve()
            if os.path.commonpath((str(cache_root), str(cache_path))) != str(
                cache_root
            ):
                raise WritePlanError("自检发现工具缓存越过一次性临时目录。")
        if unbound_name in tool_environment or "PATH" not in tool_environment:
            raise WritePlanError("自检发现工具子进程环境未按白名单构造。")
        for forbidden in ("HOME", "PYTHONPATH", "VIRTUAL_ENV"):
            if forbidden in tool_environment:
                raise WritePlanError("自检发现工具环境透传了禁止变量：%s" % forbidden)
        root = Path(directory) / "project"
        root.mkdir()
        try:
            _require_prepared_runner(
                root, ["uv", "run", "--locked", "--no-sync", "python"]
            )
        except WritePlanError:
            pass
        else:
            raise WritePlanError("自检未阻断缺少既有 .venv 的 uv runner。")
        for prefix in (
            ["poetry", "run", "python"],
            ["pipenv", "run", "python"],
            ["pdm", "run", "python"],
        ):
            try:
                _require_prepared_runner(root, prefix)
            except WritePlanError:
                pass
            else:
                raise WritePlanError("自检未阻断缺少既有 .venv 的 runner。")
        (root / ".tide").mkdir()
        (root / ".tide" / "rules").mkdir()
        profile = {
            "evidence": ["tests/test_api_evidence.py"],
            "project_kind": "python-pytest",
            "python": {
                "constraint": ">=3.8",
                "status": "confirmed",
                "evidence": ["pyproject.toml"],
            },
            "pytest_runner": {"argv_prefix": [], "status": "unknown", "evidence": []},
            "runtime_environment_variables": [
                {
                    "name": "API_BASE_URL",
                    "role": "target_url",
                    "required": True,
                    "sensitive": False,
                    "status": "confirmed",
                    "evidence": ["tests/conftest.py"],
                },
                {
                    "name": "API_TEST_ACCOUNT",
                    "role": "credential",
                    "required": True,
                    "sensitive": True,
                    "status": "confirmed",
                    "evidence": ["tests/conftest.py"],
                },
                {
                    "name": "API_TEST_PASSWORD",
                    "role": "credential",
                    "required": True,
                    "sensitive": True,
                    "status": "confirmed",
                    "evidence": ["tests/conftest.py"],
                },
            ],
        }
        profile_bytes = (
            json.dumps(
                profile, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            + "\n"
        ).encode("utf-8")
        rule_bytes = (
            '<!-- tide-evidence: ["tests/test_api_evidence.py"] -->\n# 项目规则\n'
        ).encode("utf-8")
        (root / ".tide" / "project-profile.json").write_bytes(profile_bytes)
        (root / ".tide" / "rules" / "observed.md").write_bytes(rule_bytes)
        rule_entries = [{"path": "observed.md", "sha256": _sha256(rule_bytes)}]
        (root / "tests").mkdir()
        (root / "tests" / "conftest.py").write_text(
            (
                "import os\n\n"
                "API_BASE_URL = os.environ['API_BASE_URL']\n"
                "API_TEST_ACCOUNT = os.environ['API_TEST_ACCOUNT']\n"
                "API_TEST_PASSWORD = os.environ['API_TEST_PASSWORD']\n"
            ),
            encoding="utf-8",
        )
        (root / "tests" / "test_api_evidence.py").write_text(
            (
                "def test_list(client):\n"
                "    client.get('/items', params={'skip': 0, 'limit': 10})\n"
            ),
            encoding="utf-8",
        )
        plan_path = Path(directory) / "plan.json"
        plan = {
            "run_id": "tide-self-test",
            "environment": "test",
            "scenario_ids": ["scenario-request-001"],
            "target_env_var": "API_BASE_URL",
            "runtime_env_vars": ["API_TEST_ACCOUNT", "API_TEST_PASSWORD"],
            "source_summary_sha256": "a" * 64,
            "scenario_plan_sha256": "b" * 64,
            "project_profile_sha256": _sha256(profile_bytes),
            "project_rules_sha256": _sha256(
                json.dumps(
                    rule_entries,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ),
            "generation_status": "PASS",
            "files": [
                {
                    "relative_path": "tests/test_generated.py",
                    "content": "def test_generated():\n    return None\n",
                }
            ],
        }
        candidate_path = Path(directory) / "candidate.json"
        candidate_path.write_text(
            json.dumps(
                {
                    "scenario_ids": plan["scenario_ids"],
                    "files": [
                        {
                            "relative_path": "tests/test_bound.py",
                            "content": "def test_bound():\n    return None\n",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        har_path = Path(directory) / "input.har"
        har_path.write_text(
            json.dumps(
                {
                    "log": {
                        "entries": [
                            {
                                "request": {
                                    "method": "GET",
                                    "url": "https://example.test/items",
                                },
                                "response": {
                                    "status": 200,
                                    "content": {
                                        "mimeType": "application/json",
                                        "text": "{}",
                                    },
                                },
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        summary_path = Path(directory) / "summary.json"
        sanitize(har_path, summary_path, DEFAULT_MAX_BYTES, DEFAULT_MAX_ENTRIES)
        analysis_path = Path(directory) / "analysis.json"
        analysis_path.write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "scenarios": [
                        {
                            "scenario_id": "scenario-request-001",
                            "title": "已录制接口的成功响应契约",
                            "entry_ids": ["entry-000001"],
                            "preconditions": ["使用项目画像已确认的目标环境配置"],
                            "steps": ["按项目既有客户端约定发送该接口请求"],
                            "expected_layers": [1, 2],
                            "evidence": ["entry-000001"],
                        }
                    ],
                    "questions": [],
                    "excluded": [],
                    "privacy_findings": [],
                }
            ),
            encoding="utf-8",
        )
        scenarios_path = Path(directory) / "scenarios.json"
        scenarios = bind_scenario_plan(
            root, summary_path, analysis_path, scenarios_path
        )
        bound_path = Path(directory) / "bound-plan.json"
        bound = bind_candidate(
            root,
            candidate_path,
            scenarios_path,
            scenarios["plan_digest"],
            "test",
            bound_path,
        )
        if not RUN_ID_PATTERN.fullmatch(bound["run_id"]):
            raise WritePlanError("自检生成了无效运行编号。")
        status, _ = validate_candidates(root, bound_path, ["tests"])
        if status != "SKIPPED":
            raise WritePlanError("自检项目没有静态检查证据时不应执行 Ruff。")
        invalid_syntax = dict(bound)
        invalid_syntax["files"] = [
            {
                "relative_path": "tests/test_invalid_syntax.py",
                "content": "def broken(:\n    pass\n",
            }
        ]
        try:
            _prepare(root, invalid_syntax, ["tests"], profile)
        except WritePlanError:
            pass
        else:
            raise WritePlanError("自检未能阻断无效 Python 语法。")
        unsafe_assert = dict(bound)
        unsafe_assert["files"] = [
            {
                "relative_path": "tests/test_unsafe_assert.py",
                "content": "def test_unsafe(response):\n    assert response.json()\n",
            }
        ]
        try:
            _prepare(root, unsafe_assert, ["tests"], profile)
        except WritePlanError:
            pass
        else:
            raise WritePlanError("自检未能阻断可能泄漏响应内容的原生 assert。")
        swallowed_exception = dict(bound)
        swallowed_exception["files"] = [
            {
                "relative_path": "tests/test_swallowed_exception.py",
                "content": (
                    "def test_swallowed(operation):\n"
                    "    try:\n"
                    "        operation()\n"
                    "    except Exception:\n"
                    "        pass\n"
                ),
            }
        ]
        try:
            _prepare(root, swallowed_exception, ["tests"], profile)
        except WritePlanError:
            pass
        else:
            raise WritePlanError("自检未能阻断吞掉异常的候选测试。")
        unsupported_parameter = dict(bound)
        unsupported_parameter["files"] = [
            {
                "relative_path": "tests/test_unsupported_parameter.py",
                "content": (
                    "def test_list(client):\n"
                    "    offset = 0\n"
                    "    while True:\n"
                    "        client.get('/items', params={'skip': offset, 'limit': 100})\n"
                    "        offset += 100\n"
                    "        break\n"
                ),
            }
        ]
        try:
            _prepare(root, unsupported_parameter, ["tests"], profile)
        except WritePlanError:
            pass
        else:
            raise WritePlanError("自检未能阻断无项目证据的请求参数常量。")
        supported_parameter = dict(bound)
        supported_parameter["files"] = [
            {
                "relative_path": "tests/test_supported_parameter.py",
                "content": (
                    "def test_list(client):\n"
                    "    offset = 0\n"
                    "    while True:\n"
                    "        client.get('/items', params={'skip': offset, 'limit': 10})\n"
                    "        offset += 10\n"
                    "        break\n"
                ),
            }
        ]
        _prepare(root, supported_parameter, ["tests"], profile)
        unsafe_failure_message = dict(bound)
        unsafe_failure_message["files"] = [
            {
                "relative_path": "tests/test_unsafe_failure_message.py",
                "content": (
                    "import pytest\n"
                    "def test_failure(response):\n"
                    "    pytest.fail(f'response={response.text}', pytrace=False)\n"
                ),
            }
        ]
        try:
            _prepare(root, unsafe_failure_message, ["tests"], profile)
        except WritePlanError:
            pass
        else:
            raise WritePlanError("自检未能阻断包含响应值的失败消息。")
        unsafe_output = dict(bound)
        unsafe_output["files"] = [
            {
                "relative_path": "tests/test_unsafe_output.py",
                "content": "def test_output(response):\n    print(response.text)\n",
            }
        ]
        try:
            _prepare(root, unsafe_output, ["tests"], profile)
        except WritePlanError:
            pass
        else:
            raise WritePlanError("自检未能阻断输出运行时响应对象。")
        try:
            validate_candidate(
                root,
                profile,
                "def incompatible(value: str | None) -> None:\n    pass\n",
                Path("tests/test_incompatible.py"),
            )
        except CandidateCheckError:
            pass
        else:
            raise WritePlanError("自检未阻断目标 Python 不兼容注解。")
        unbound_variable = dict(bound)
        unbound_variable["runtime_env_vars"] = ["UNCONFIRMED_VALUE"]
        try:
            _validate_plan_profile_binding(unbound_variable, profile)
        except WritePlanError:
            pass
        else:
            raise WritePlanError("自检未能阻断画像未确认的环境变量。")
        fake_runner = root / "fake-runner"
        fake_lock = root / "fake.lock"
        ruff_config = root / "ruff.toml"
        fake_runner.write_text(
            "#!/bin/sh\nexit 1\n",
            encoding="utf-8",
        )
        fake_runner.chmod(0o700)
        fake_lock.write_text("locked\n", encoding="utf-8")
        ruff_config.write_text("line-length = 88\n", encoding="utf-8")
        runner_key = (str(fake_runner),)
        SAFE_RUNNERS[runner_key] = fake_lock.name
        ruff_profile = dict(profile)
        ruff_profile["pytest_runner"] = {
            "argv_prefix": [str(fake_runner)],
            "status": "confirmed",
            "evidence": ["fake.lock", "ruff.toml"],
        }
        ruff_profile_bytes = (
            json.dumps(
                ruff_profile,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        (root / ".tide" / "project-profile.json").write_bytes(ruff_profile_bytes)
        ruff_plan = dict(plan)
        ruff_plan["run_id"] = "tide-ruff-reject"
        ruff_plan["project_profile_sha256"] = _sha256(ruff_profile_bytes)
        ruff_plan["files"] = [
            {
                "relative_path": "tests/test_ruff_rejected.py",
                "content": "def test_ruff_rejected():\n    return None\n",
            }
        ]
        ruff_plan_path = Path(directory) / "ruff-plan.json"
        ruff_plan_path.write_text(json.dumps(ruff_plan), encoding="utf-8")
        pass_candidate_path = Path(directory) / "ruff-review-candidate.json"
        pass_candidate_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "verdict": "PASS",
                    "blocking_findings": [],
                    "non_blocking_findings": [],
                    "information_gaps": [],
                }
            ),
            encoding="utf-8",
        )
        try:
            bind_review(
                root,
                ruff_plan_path,
                pass_candidate_path,
                ["tests"],
                Path(directory) / "ruff-review.json",
            )
        except WritePlanError as exc:
            if "Ruff" not in str(exc):
                raise
        else:
            raise WritePlanError("自检未阻断绕过 Ruff 校验后绑定 PASS 审查。")
        try:
            execute(
                root,
                ruff_plan_path,
                pass_candidate_path,
                ["tests"],
                preflight=True,
            )
        except WritePlanError as exc:
            if "Ruff" not in str(exc):
                raise
        else:
            raise WritePlanError("自检未阻断绕过 Ruff 校验后取得写入授权。")
        SAFE_RUNNERS.pop(runner_key)
        fake_runner.unlink()
        fake_lock.unlink()
        ruff_config.unlink()
        (root / ".tide" / "project-profile.json").write_bytes(profile_bytes)
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        plan_digest = _plan_digest(plan)
        review_candidate_path = Path(directory) / "review-candidate.json"
        review_candidate = {
            "schema_version": "1.0",
            "verdict": "PASS",
            "blocking_findings": [],
            "non_blocking_findings": [],
            "information_gaps": [],
        }
        review_candidate_path.write_text(json.dumps(review_candidate), encoding="utf-8")
        review_path = Path(directory) / "review.json"
        review = bind_review(
            root, plan_path, review_candidate_path, ["tests"], review_path
        )
        if review["reviewed_plan_sha256"] != plan_digest:
            raise WritePlanError("自检审查绑定未使用当前计划摘要。")
        if not HASH_PATTERN.fullmatch(review["candidate_validation_sha256"]):
            raise WritePlanError("自检审查未绑定候选机械校验摘要。")
        _, _, write_digest = execute(
            root, plan_path, review_path, ["tests"], preflight=True
        )
        execute(
            root, plan_path, review_path, ["tests"], confirmed_write_digest=write_digest
        )
        created = root / "tests" / "test_generated.py"
        manifest = root / ".tide" / "runs" / "tide-self-test" / "manifest.json"
        if not created.is_file() or not manifest.is_file():
            raise WritePlanError("自检未创建预期文件。")
        try:
            execute(root, plan_path, review_path, ["tests"], preflight=True)
        except WritePlanError:
            pass
        else:
            raise WritePlanError("自检未能阻断覆盖。")
        invalid_environment = dict(plan)
        invalid_environment["environment"] = "local-docker-compose"
        try:
            _load_plan_value(invalid_environment)
        except WritePlanError:
            pass
        else:
            raise WritePlanError("自检未能阻断脚本不支持的环境别名。")


def build_parser():
    parser = argparse.ArgumentParser(
        description="校验写入计划，只新增测试文件和脱敏运行记录。"
    )
    parser.add_argument("--project-root", help="目标项目根目录")
    parser.add_argument("--plan", help="系统临时目录中的写入计划 JSON")
    parser.add_argument(
        "--review", help="系统临时目录中绑定当前计划且已通过的审查 JSON"
    )
    parser.add_argument("--review-candidate", help="审查角色返回的语义结论 JSON")
    parser.add_argument(
        "--test-dir",
        action="append",
        default=[],
        help="用户确认的项目内现有测试目录，可重复",
    )
    parser.add_argument(
        "--confirmed-write-digest", help="用户确认的当前写入授权 SHA-256 摘要"
    )
    parser.add_argument("--candidate", help="生成角色返回的候选 JSON")
    parser.add_argument("--scenarios", help="bind_scenarios.py 生成的场景计划")
    parser.add_argument(
        "--confirmed-scenario-digest", help="用户确认的当前场景计划摘要"
    )
    parser.add_argument("--environment", help="用户确认的环境名")
    parser.add_argument("--output", help="绑定后的写入计划输出路径")
    parser.add_argument(
        "--bind-candidate",
        action="store_true",
        help="由脚本生成运行编号和证据散列并绑定候选",
    )
    parser.add_argument(
        "--validate-candidates",
        action="store_true",
        help="对候选执行语法和项目已有 Ruff 检查",
    )
    parser.add_argument(
        "--bind-review",
        action="store_true",
        help="由脚本绑定审查结论、当前计划摘要和完整文件范围",
    )
    parser.add_argument(
        "--inspect-plan", action="store_true", help="只校验计划结构并输出计划摘要"
    )
    parser.add_argument(
        "--preflight", action="store_true", help="只校验，不写入任何文件"
    )
    parser.add_argument("--self-test", action="store_true", help="运行内置自检后退出")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print("write_run.py 自检通过。")
            return 0
        if args.bind_candidate:
            required = (
                args.project_root,
                args.candidate,
                args.scenarios,
                args.confirmed_scenario_digest,
                args.environment,
                args.output,
            )
            if not all(required):
                raise WritePlanError(
                    "绑定候选必须提供项目、候选、已确认场景、环境和输出路径。"
                )
            plan = bind_candidate(
                Path(args.project_root),
                Path(args.candidate),
                Path(args.scenarios),
                args.confirmed_scenario_digest,
                args.environment,
                Path(args.output),
            )
            print(
                "候选绑定完成：%s；计划摘要：%s。"
                % (plan["run_id"], _plan_digest(plan))
            )
            return 0
        if args.validate_candidates:
            if not args.project_root or not args.plan or not args.test_dir:
                raise WritePlanError("候选校验必须提供项目、计划和测试目录。")
            status, detail = validate_candidates(
                Path(args.project_root), Path(args.plan), args.test_dir
            )
            print("候选机械校验：%s；%s。" % (status, detail))
            return 0
        if args.bind_review:
            if (
                not args.project_root
                or not args.plan
                or not args.review_candidate
                or not args.test_dir
                or not args.output
            ):
                raise WritePlanError(
                    "绑定审查必须提供项目、计划、审查候选、测试目录和输出路径。"
                )
            review = bind_review(
                Path(args.project_root),
                Path(args.plan),
                Path(args.review_candidate),
                args.test_dir,
                Path(args.output),
            )
            print(
                "审查绑定完成：计划摘要 %s，共 %d 个文件。"
                % (review["reviewed_plan_sha256"], len(review["verified_scope"]))
            )
            return 0
        if args.inspect_plan:
            if not args.plan:
                raise WritePlanError("检查计划必须提供 --plan。")
            plan = _load_plan(Path(args.plan))
            print("写入计划结构有效；计划摘要：%s。" % _plan_digest(plan))
            return 0
        if not args.project_root or not args.plan or not args.review:
            raise WritePlanError("必须提供 --project-root、--plan 和 --review。")
        if not args.preflight and not args.confirmed_write_digest:
            raise WritePlanError("实际写入必须提供 --confirmed-write-digest。")
        run_id, file_count, write_digest = execute(
            Path(args.project_root),
            Path(args.plan),
            Path(args.review),
            args.test_dir,
            confirmed_write_digest=args.confirmed_write_digest,
            preflight=args.preflight,
        )
        action = "预检通过" if args.preflight else "写入完成"
        print(
            "%s：%s，共 %d 个测试文件；写入授权摘要：%s。"
            % (action, run_id, file_count, write_digest)
        )
        return 0
    except (OSError, WritePlanError) as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
