#!/usr/bin/env python3
"""严格校验脱敏摘要与场景分析，并绑定为可确认计划。"""

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path

from derive_scenarios import ScenarioDerivationError, derive
from sanitize_har import SanitizationError, load_summary

MAX_BYTES = 8 * 1024 * 1024
SCENARIO_ID = re.compile(r"scenario-[a-z0-9][a-z0-9-]{1,63}")
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
ABSOLUTE_PATH = re.compile(
    r"(?:^|[\s`\"'(=])(?:/(?:Applications|Library|System|Users|Volumes|etc|home|mnt|opt|private|root|tmp|usr|var|workspace)(?:/|\b)|\\\\|[A-Za-z]:[\\/]|~[/\\])"
)
RAW_URL = re.compile(r"https?://", re.IGNORECASE)
EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
SECRET_ASSIGNMENT = re.compile(
    r"(?:authorization|cookie|password|secret|token|api[_-]?key)\s*[:=]",
    re.IGNORECASE,
)
OPAQUE_VALUE = re.compile(r"\b(?:[0-9a-f]{32,}|[A-Za-z0-9_+/=-]{40,})\b")


class ScenarioBindingError(Exception):
    pass


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _is_within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _read_temp_json(path, label):
    if path.is_symlink() or not path.is_file():
        raise ScenarioBindingError("%s必须是普通文件。" % label)
    resolved = path.resolve(strict=True)
    if not _is_within(resolved, Path(tempfile.gettempdir()).resolve()):
        raise ScenarioBindingError("%s必须位于系统临时目录。" % label)
    info = os.stat(str(resolved), follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
        raise ScenarioBindingError("%s大小或类型无效。" % label)
    try:
        value = json.loads(
            resolved.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise ScenarioBindingError("%s不是有效 JSON：%s" % (label, exc))
    if not isinstance(value, dict):
        raise ScenarioBindingError("%s顶层必须是对象。" % label)
    return value


def _safe_text(value, label):
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 500
        or "\x00" in value
        or ABSOLUTE_PATH.search(value)
        or RAW_URL.search(value)
        or EMAIL.search(value)
        or SECRET_ASSIGNMENT.search(value)
        or OPAQUE_VALUE.search(value)
    ):
        raise ScenarioBindingError("%s必须是不含绝对路径的非空字符串。" % label)


def _string_list(value, label):
    if not isinstance(value, list):
        raise ScenarioBindingError("%s必须是数组。" % label)
    for index, item in enumerate(value):
        _safe_text(item, "%s[%d]" % (label, index))


def validate_analysis(analysis, entry_ids):
    expected = {"status", "scenarios", "questions", "excluded", "privacy_findings"}
    if set(analysis) != expected:
        raise ScenarioBindingError("场景分析字段不完整或包含未知字段。")
    if analysis["status"] not in {"PASS", "PARTIAL", "BLOCKED"}:
        raise ScenarioBindingError("场景分析状态无效。")
    for field in ("questions", "excluded", "privacy_findings"):
        _string_list(analysis[field], field)
    if analysis["status"] == "BLOCKED" or analysis["privacy_findings"]:
        raise ScenarioBindingError("场景分析已阻断或包含隐私发现。")
    scenarios = analysis["scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        raise ScenarioBindingError("场景分析必须包含至少一个场景。")
    seen_scenarios = set()
    referenced_entries = set()
    expected_scenario = {
        "scenario_id",
        "title",
        "entry_ids",
        "preconditions",
        "steps",
        "expected_layers",
        "evidence",
    }
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict) or set(scenario) != expected_scenario:
            raise ScenarioBindingError("scenarios[%d]字段无效。" % index)
        scenario_id = scenario["scenario_id"]
        if (
            not isinstance(scenario_id, str)
            or SCENARIO_ID.fullmatch(scenario_id) is None
            or scenario_id in seen_scenarios
        ):
            raise ScenarioBindingError("场景编号无效或重复。")
        seen_scenarios.add(scenario_id)
        _safe_text(scenario["title"], "场景标题")
        _string_list(scenario["entry_ids"], "场景 entry_ids")
        if not scenario["entry_ids"] or len(set(scenario["entry_ids"])) != len(
            scenario["entry_ids"]
        ):
            raise ScenarioBindingError("场景 entry_ids 不能为空或重复。")
        unknown = set(scenario["entry_ids"]) - entry_ids
        if unknown:
            raise ScenarioBindingError(
                "场景引用不存在的 entry_id：%s" % "、".join(sorted(unknown))
            )
        referenced_entries.update(scenario["entry_ids"])
        _string_list(scenario["preconditions"], "场景前置条件")
        _string_list(scenario["steps"], "场景步骤")
        _string_list(scenario["evidence"], "场景证据")
        if not set(scenario["evidence"]).issubset(set(scenario["entry_ids"])):
            raise ScenarioBindingError("场景证据只能引用该场景已有 entry_id。")
        layers = scenario["expected_layers"]
        if (
            not isinstance(layers, list)
            or not layers
            or any(
                type(layer) is not int or layer not in range(1, 6) for layer in layers
            )
        ):
            raise ScenarioBindingError("场景断言层级必须是 1 至 5 的非空整数数组。")
        if len(set(layers)) != len(layers):
            raise ScenarioBindingError("场景断言层级不能重复。")
        if any(layer not in {1, 2, 3} for layer in layers):
            raise ScenarioBindingError(
                "仅由脱敏 HAR 确定的场景只能绑定第 1 至 3 层断言。"
            )
    return sorted(seen_scenarios), sorted(referenced_entries)


def _reject_duplicate_keys(pairs):
    value = {}
    for key, child in pairs:
        if key in value:
            raise ScenarioBindingError("JSON 包含重复字段：%s" % key)
        value[key] = child
    return value


def _project_digests(root):
    profile = root / ".tide" / "project-profile.json"
    rules = root / ".tide" / "rules"
    if (
        profile.is_symlink()
        or not profile.is_file()
        or rules.is_symlink()
        or not rules.is_dir()
    ):
        raise ScenarioBindingError("目标项目缺少安全的 Tide 画像或规则。")
    profile_bytes = profile.read_bytes()
    entries = []
    for path in sorted(rules.rglob("*")):
        if path.is_symlink() or (path.is_file() and path.suffix.lower() != ".md"):
            raise ScenarioBindingError("项目规则目录包含不安全文件。")
        if path.is_file():
            entries.append(
                {
                    "path": path.relative_to(rules).as_posix(),
                    "sha256": _sha256(path.read_bytes()),
                }
            )
    if not entries:
        raise ScenarioBindingError("项目规则目录为空。")
    return _sha256(profile_bytes), _sha256(_canonical(entries))


def _write_new(path, value):
    parent = path.parent.resolve(strict=True)
    if not _is_within(parent, Path(tempfile.gettempdir()).resolve()):
        raise ScenarioBindingError("场景计划只能写入系统临时目录。")
    if path.exists() or path.is_symlink():
        raise ScenarioBindingError("拒绝覆盖既有场景计划。")
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor = os.open(
        str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def bind(project_root, summary_path, analysis_path, output_path):
    root = project_root.resolve(strict=True)
    if project_root.is_symlink() or not root.is_dir():
        raise ScenarioBindingError("目标项目根目录无效。")
    try:
        summary, summary_bytes = load_summary(summary_path)
    except SanitizationError as exc:
        raise ScenarioBindingError(str(exc))
    if not _is_within(
        summary_path.resolve(strict=True), Path(tempfile.gettempdir()).resolve()
    ):
        raise ScenarioBindingError("脱敏摘要必须位于系统临时目录。")
    analysis = _read_temp_json(analysis_path, "场景分析")
    try:
        deterministic_analysis = derive(summary)
    except ScenarioDerivationError as exc:
        raise ScenarioBindingError(str(exc))
    if analysis != deterministic_analysis:
        raise ScenarioBindingError("场景分析未逐字段绑定当前脱敏摘要的确定性结果。")
    entry_ids = {entry["entry_id"] for entry in summary["entries"]}
    scenario_ids, referenced_entries = validate_analysis(analysis, entry_ids)
    profile_sha256, rules_sha256 = _project_digests(root)
    payload = {
        "schema_version": "1.0",
        "kind": "tide-scenarios",
        "source_summary_sha256": _sha256(summary_bytes),
        "project_profile_sha256": profile_sha256,
        "project_rules_sha256": rules_sha256,
        "analysis": analysis,
        "analysis_sha256": _sha256(_canonical(analysis)),
        "confirmation_summary": {
            "status": analysis["status"],
            "scenario_ids": scenario_ids,
            "referenced_entry_ids": referenced_entries,
            "questions": analysis["questions"],
            "excluded": analysis["excluded"],
        },
    }
    payload["plan_digest"] = _sha256(_canonical(payload))
    _write_new(output_path, payload)
    return payload


def self_test():
    from sanitize_har import DEFAULT_MAX_BYTES, DEFAULT_MAX_ENTRIES, sanitize

    with tempfile.TemporaryDirectory(prefix="tide-scenario-test-") as directory:
        root = Path(directory)
        project = root / "project"
        (project / ".tide" / "rules").mkdir(parents=True)
        (project / ".tide" / "project-profile.json").write_text(
            "{}\n", encoding="utf-8"
        )
        (project / ".tide" / "rules" / "observed.md").write_text(
            "# 规则\n", encoding="utf-8"
        )
        har = root / "input.har"
        summary = root / "summary.json"
        har.write_text(
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
        sanitize(har, summary, DEFAULT_MAX_BYTES, DEFAULT_MAX_ENTRIES)
        loaded_summary, _ = load_summary(summary)
        analysis = derive(loaded_summary)
        analysis_path = root / "analysis.json"
        analysis_path.write_text(json.dumps(analysis), encoding="utf-8")
        output = root / "scenarios.json"
        plan = bind(project, summary, analysis_path, output)
        if not HASH_PATTERN.fullmatch(plan["plan_digest"]):
            raise ScenarioBindingError("自检未生成有效摘要。")
        invalid = dict(analysis)
        invalid["scenarios"] = [dict(analysis["scenarios"][0])]
        invalid["scenarios"][0]["entry_ids"] = ["entry-999999"]
        try:
            validate_analysis(invalid, {"entry-000001"})
        except ScenarioBindingError:
            pass
        else:
            raise ScenarioBindingError("自检未阻断未知 entry_id。")
        invalid_layers = dict(analysis)
        invalid_layers["scenarios"] = [dict(analysis["scenarios"][0])]
        invalid_layers["scenarios"][0]["scenario_id"] = "scenario-request-renamed"
        invalid_layers["scenarios"][0]["expected_layers"] = [1, 2, 3, 4, 5]
        try:
            validate_analysis(invalid_layers, {"entry-000001"})
        except ScenarioBindingError:
            pass
        else:
            raise ScenarioBindingError("自检未阻断 HAR CRUD 场景越界断言层级。")
        renamed = dict(analysis)
        renamed["scenarios"] = [dict(analysis["scenarios"][0])]
        renamed["scenarios"][0]["scenario_id"] = "scenario-request-renamed"
        renamed_path = root / "renamed-analysis.json"
        renamed_path.write_text(json.dumps(renamed), encoding="utf-8")
        try:
            bind(project, summary, renamed_path, root / "renamed-plan.json")
        except ScenarioBindingError:
            pass
        else:
            raise ScenarioBindingError("自检未阻断改名后的非确定性场景分析。")
        _safe_text("调用 /api/v1/items 路由", "接口路由样本")
        try:
            _safe_text("读取 /Users/example/project/file.py", "本地路径样本")
        except ScenarioBindingError:
            pass
        else:
            raise ScenarioBindingError("自检未阻断常见本地绝对路径。")


def parser():
    value = argparse.ArgumentParser(
        description="校验脱敏摘要与场景分析，并绑定确认计划。"
    )
    value.add_argument("--project-root", help="已初始化目标项目")
    value.add_argument("--summary", help="sanitize_har.py 生成的脱敏摘要")
    value.add_argument("--analysis", help="derive_scenarios.py 生成的 JSON")
    value.add_argument("--output", help="系统临时目录中的新场景计划")
    value.add_argument("--self-test", action="store_true", help="运行隔离自检")
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print("bind_scenarios.py 自检通过。")
            return 0
        if not all((args.project_root, args.summary, args.analysis, args.output)):
            raise ScenarioBindingError("必须提供项目、摘要、分析和输出路径。")
        plan = bind(
            Path(args.project_root),
            Path(args.summary),
            Path(args.analysis),
            Path(args.output),
        )
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
    except (OSError, ScenarioBindingError) as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
