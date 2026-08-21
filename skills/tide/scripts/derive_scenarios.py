#!/usr/bin/env python3
"""从脱敏 HAR 摘要确定性提取可确认的接口场景。"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from sanitize_har import SanitizationError, load_summary


class ScenarioDerivationError(Exception):
    pass


def _is_json_success(entry):
    body = entry["response_body"]
    return (
        200 <= entry["response_status"] < 300
        and body["mime_type"] == "application/json"
        and body["schema"]["type"] in {"object", "array"}
    )


def _path(entry):
    return tuple(entry["url"]["path_aliases"])


def _host(entry):
    return entry["url"]["host_alias"]


def _first_after(entries, start, predicate):
    for index in range(start + 1, len(entries)):
        if predicate(entries[index]):
            return index
    return None


def derive(summary):
    entries = summary["entries"]
    scenarios = []
    used = set()
    for create_index, create in enumerate(entries):
        if create["method"] != "POST" or not _is_json_success(create):
            continue
        base = _path(create)
        host = _host(create)
        if not base:
            continue

        def collection_get(item):
            return (
                item["method"] == "GET"
                and _host(item) == host
                and _path(item) == base
                and _is_json_success(item)
            )

        def item_method(method):
            def matches(item):
                path = _path(item)
                return (
                    item["method"] == method
                    and _host(item) == host
                    and len(path) == len(base) + 1
                    and path[:-1] == base
                    and path[-1] in {"<uuid>", "<integer>"}
                    and _is_json_success(item)
                )

            return matches

        query_after_create = _first_after(entries, create_index, collection_get)
        update_index = _first_after(entries, create_index, item_method("PUT"))
        if update_index is None:
            update_index = _first_after(entries, create_index, item_method("PATCH"))
        delete_index = _first_after(entries, create_index, item_method("DELETE"))
        if update_index is None or delete_index is None or update_index >= delete_index:
            continue
        query_after_update = _first_after(entries, update_index, collection_get)
        query_after_delete = _first_after(entries, delete_index, collection_get)
        ordered = [create_index]
        for candidate in (
            query_after_create,
            update_index,
            query_after_update,
            delete_index,
            query_after_delete,
        ):
            if candidate is not None and candidate not in ordered:
                ordered.append(candidate)
        if len(ordered) < 4:
            continue
        entry_ids = [entries[index]["entry_id"] for index in ordered]
        scenarios.append(
            {
                "scenario_id": "scenario-crud-%03d" % (len(scenarios) + 1),
                "title": "资源创建、查询、更新与删除闭环",
                "entry_ids": entry_ids,
                "preconditions": ["使用项目画像已确认的认证与目标环境配置"],
                "steps": [
                    "创建一条带唯一测试标识的资源",
                    "查询并确认新资源可见",
                    "更新该资源并确认状态变化",
                    "删除该资源并确认列表中不再存在",
                ],
                "expected_layers": [1, 2, 3],
                "evidence": entry_ids,
            }
        )
        used.update(entry_ids)

    if not scenarios:
        seen = set()
        for entry in entries:
            if not _is_json_success(entry):
                continue
            signature = (_host(entry), entry["method"], _path(entry))
            if signature in seen:
                continue
            seen.add(signature)
            entry_id = entry["entry_id"]
            scenarios.append(
                {
                    "scenario_id": "scenario-request-%03d" % (len(scenarios) + 1),
                    "title": "已录制接口的成功响应契约",
                    "entry_ids": [entry_id],
                    "preconditions": ["使用项目画像已确认的目标环境配置"],
                    "steps": ["按项目既有客户端约定发送该接口请求"],
                    "expected_layers": [1, 2],
                    "evidence": [entry_id],
                }
            )
            used.add(entry_id)

    if not scenarios:
        raise ScenarioDerivationError("脱敏摘要中没有可生成的成功 JSON 接口场景。")

    failed = sum(1 for entry in entries if entry["response_status"] >= 500)
    non_json = sum(1 for entry in entries if not _is_json_success(entry)) - failed
    repeated = len(entries) - len(used) - failed - max(non_json, 0)
    excluded = []
    if failed:
        excluded.append("已排除 %d 条服务端失败响应" % failed)
    if non_json > 0:
        excluded.append("已排除 %d 条非成功 JSON 响应" % non_json)
    if repeated > 0:
        excluded.append("已排除 %d 条重复或不属于完整闭环的接口记录" % repeated)
    return {
        "status": "PASS",
        "scenarios": scenarios,
        "questions": [],
        "excluded": excluded,
        "privacy_findings": [],
    }


def _write_new(path, value):
    parent = path.parent.resolve(strict=True)
    try:
        parent.relative_to(Path(tempfile.gettempdir()).resolve())
    except ValueError:
        raise ScenarioDerivationError("场景分析只能写入系统临时目录。")
    if path.exists() or path.is_symlink():
        raise ScenarioDerivationError("拒绝覆盖既有场景分析。")
    data = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor = os.open(
        str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def self_test():
    summary = {
        "entries": [
            {
                "entry_id": "entry-%06d" % (index + 1),
                "method": method,
                "url": {
                    "scheme": "http",
                    "host_alias": "host_000001",
                    "path_aliases": ["segment_000001", "segment_000002"]
                    + (["<uuid>"] if item else []),
                },
                "response_status": 200,
                "response_body": {
                    "mime_type": "application/json",
                    "schema": {"type": "object", "fields": {}},
                },
            }
            for index, (method, item) in enumerate(
                (
                    ("POST", False),
                    ("GET", False),
                    ("PUT", True),
                    ("DELETE", True),
                    ("GET", False),
                )
            )
        ]
    }
    result = derive(summary)
    assert result["status"] == "PASS"
    assert len(result["scenarios"]) == 1
    assert result["scenarios"][0]["expected_layers"] == [1, 2, 3]
    assert len(result["scenarios"][0]["entry_ids"]) == 5
    print("derive_scenarios.py 自检通过。")


def parser():
    value = argparse.ArgumentParser(description="从脱敏 HAR 摘要确定性提取接口场景。")
    value.add_argument("--summary", help="sanitize_har.py 生成的系统临时摘要。")
    value.add_argument("--output", help="新建的系统临时场景分析 JSON。")
    value.add_argument("--self-test", action="store_true", help="运行隔离自检。")
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.summary or not args.output:
        parser().error("必须同时提供 --summary 和 --output")
    try:
        summary, _ = load_summary(Path(args.summary))
        analysis = derive(summary)
        _write_new(Path(args.output), analysis)
        print("场景分析已由脚本生成，共 %d 个场景。" % len(analysis["scenarios"]))
        return 0
    except (OSError, SanitizationError, ScenarioDerivationError) as exc:
        print("场景提取失败：%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
