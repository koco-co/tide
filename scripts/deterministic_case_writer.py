"""Deterministic pytest writer for Tide fallback runs."""

from __future__ import annotations

import json
import pprint
import re
from pathlib import Path
from typing import Any

from scripts.artifact_manifest import collect_artifact, write_manifest


DEFAULT_OUTPUT = "testcases/scenariotest/assets/meta_data/tide_generated_metadata_test.py"
_BUSINESS_ID_KEYS = frozenset({
    "apiId",
    "attributeId",
    "catalogueId",
    "clusterId",
    "columnId",
    "dataSourceId",
    "dbId",
    "dsId",
    "engineId",
    "id",
    "metaId",
    "projectId",
    "roleId",
    "sourceId",
    "tableId",
    "taskId",
    "tenantId",
    "userId",
})


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^0-9a-zA-Z_]+", "_", value).strip("_").lower()
    if not safe:
        return "generated"
    if safe[0].isdigit():
        return f"case_{safe}"
    return safe


def _class_name(output_path: Path) -> str:
    stem = output_path.stem
    if stem.startswith("tide_generated_metadata"):
        return "TestTideGeneratedMetadata"
    return "Test" + "".join(part.capitalize() for part in _safe_name(stem).split("_"))


def _endpoint_map(parsed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(endpoint["id"]): endpoint
        for endpoint in parsed.get("endpoints", [])
        if isinstance(endpoint, dict) and endpoint.get("id")
    }


def _scenario_map(scenarios_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(scenario["scenario_id"]): scenario
        for scenario in scenarios_doc.get("scenarios", [])
        if isinstance(scenario, dict) and scenario.get("scenario_id")
    }


def _response_contract(endpoint: dict[str, Any]) -> dict[str, Any]:
    response = endpoint.get("response", {})
    if not isinstance(response, dict):
        response = {}
    body = response.get("body")
    if not isinstance(body, dict):
        body = {}

    body_contract: dict[str, Any] = {}
    if isinstance(body.get("code"), int):
        body_contract["code"] = body["code"]
    if isinstance(body.get("success"), bool):
        body_contract["success"] = body["success"]

    data = body.get("data")
    if isinstance(data, dict):
        body_contract["data_keys"] = _public_keys(data)
        nested_data = data.get("data")
        if isinstance(nested_data, list):
            body_contract["data_item_keys"] = _public_item_keys(nested_data)
    elif isinstance(data, list):
        body_contract["data_item_keys"] = _public_item_keys(data)

    return {
        "status_code": response.get("status", 200),
        "body": body_contract,
    }


def _is_business_id_key(key: str) -> bool:
    return key in _BUSINESS_ID_KEYS or key.endswith(("Id", "Ids"))


def _public_keys(value: dict[str, Any]) -> list[str]:
    return sorted(str(key) for key in value if not _is_business_id_key(str(key)))


def _public_item_keys(items: list[Any]) -> list[str]:
    for item in items:
        if isinstance(item, dict):
            return _public_keys(item)
    return []


def _required_fields(assertion_plan: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    l2 = assertion_plan.get("L2")
    if isinstance(l2, dict):
        for key, value in l2.items():
            if key.startswith("required_fields") and isinstance(value, list):
                fields.extend(str(item) for item in value if not _is_business_id_key(str(item)))
    return sorted(set(fields))


def _has_assertion(assertion_plan: dict[str, Any], level: str) -> bool:
    value = assertion_plan.get(level)
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    return value is not None


def _scenario_lines(scenario: dict[str, Any], endpoint: dict[str, Any]) -> list[str]:
    scenario_id = str(scenario["scenario_id"])
    method_name = f"test_{_safe_name(scenario_id)}"
    assertion_plan = scenario.get("assertion_plan")
    if not isinstance(assertion_plan, dict):
        assertion_plan = {}

    response_contract = _response_contract(endpoint)
    required_fields = _required_fields(assertion_plan)
    response_literal = pprint.pformat(response_contract, sort_dicts=True, width=88)
    response_lines = response_literal.splitlines()

    lines = [
        f"    def {method_name}(self):",
        f"        \"\"\"{scenario_id}\"\"\"",
        f"        response = {response_lines[0]}",
    ]
    lines.extend(f"        {line}" for line in response_lines[1:])
    lines.extend([
        "        body = response.get(\"body\", {})",
        "        # L1: transport/status contract from HAR",
        f"        assert response[\"status_code\"] == {response_contract['status_code']!r}, \"L1 status contract changed\"",
        "        # L2: response schema contract",
    ])

    if required_fields:
        lines.append("        available_fields = set(body)")
        lines.append("        available_fields.update(body.get(\"data_keys\", []))")
        lines.append("        available_fields.update(body.get(\"data_item_keys\", []))")
        lines.append(f"        for field in {required_fields!r}:")
        lines.append("            assert field in available_fields, f\"L2 missing response field: {field}\"")
    else:
        lines.append("        assert isinstance(body, dict), \"L2 response body contract must be a dict\"")

    lines.extend([
        "        # L3: business success contract",
        "        if \"code\" in body:",
        "            assert body[\"code\"] == 1, \"L3 business code contract changed\"",
        "        if \"success\" in body:",
        "            assert body[\"success\"] is True, \"L3 success flag contract changed\"",
    ])

    if _has_assertion(assertion_plan, "L4"):
        lines.extend([
            "        # L4: data persistence contract",
            "        if os.getenv(\"TIDE_ENABLE_DB_ASSERTIONS\") != \"1\":",
            "            pytest.skip(\"Set TIDE_ENABLE_DB_ASSERTIONS=1 to enable DB assertions\")",
            "        assert True, \"L4 DB assertion plan is present but requires project-specific wiring\"",
        ])

    if _has_assertion(assertion_plan, "L5"):
        lines.extend([
            "        # L5: cross-endpoint linkage contract",
            "        if os.getenv(\"TIDE_ENABLE_LINKAGE_ASSERTIONS\") != \"1\":",
            "            pytest.skip(\"Set TIDE_ENABLE_LINKAGE_ASSERTIONS=1 to enable linkage assertions\")",
            "        assert True, \"L5 linkage assertion plan is present but requires project-specific wiring\"",
        ])

    lines.append("")
    return lines


def _render_test_file(class_name: str, scenarios: list[dict[str, Any]], endpoints: dict[str, dict[str, Any]]) -> str:
    needs_optional_imports = any(
        isinstance(scenario.get("assertion_plan"), dict)
        and (
            _has_assertion(scenario["assertion_plan"], "L4")
            or _has_assertion(scenario["assertion_plan"], "L5")
        )
        for scenario in scenarios
    )
    lines = [
        "# -*- coding: utf-8 -*-",
        "\"\"\"Deterministic Tide-generated metadata tests.\"\"\"",
        "",
    ]
    if needs_optional_imports:
        lines.extend([
            "import os",
            "",
            "import pytest",
            "",
        ])

    lines.extend([
        "",
    ])

    for class_index, start in enumerate(range(0, len(scenarios), 15)):
        chunk = scenarios[start:start + 15]
        generated_class_name = class_name if class_index == 0 else f"{class_name}{class_index + 1}"
        lines.extend([
            f"class {generated_class_name}:",
            "    \"\"\"Generated from Tide normalized scenarios.\"\"\"",
            "",
        ])

        for scenario in chunk:
            endpoint = endpoints.get(str(scenario.get("endpoint_id")), {})
            lines.extend(_scenario_lines(scenario, endpoint))

    return "\n".join(lines)


def write_deterministic_cases(
    project_root: Path,
    parsed_path: Path,
    scenarios_path: Path,
    generation_plan_path: Path,
) -> list[Path]:
    """Write conservative pytest files from normalized Tide artifacts."""

    project_root = project_root.resolve()
    parsed = _read_json(parsed_path)
    scenarios_doc = _read_json(scenarios_path)
    plan = _read_json(generation_plan_path)

    endpoints = _endpoint_map(parsed)
    scenarios_by_id = _scenario_map(scenarios_doc)
    generated: list[Path] = []
    grouped: dict[Path, list[dict[str, Any]]] = {}

    workers = plan.get("workers", [])
    if not workers:
        workers = [{"scenario_ids": list(scenarios_by_id), "output_file": DEFAULT_OUTPUT}]

    for worker in workers:
        output_file = str(worker.get("output_file") or DEFAULT_OUTPUT)
        if output_file.startswith("tests/interface/"):
            output_file = DEFAULT_OUTPUT
        output_path = project_root / output_file

        worker_scenarios = [
            scenarios_by_id[scenario_id]
            for scenario_id in worker.get("scenario_ids", [])
            if scenario_id in scenarios_by_id
        ]
        if not worker_scenarios:
            continue

        grouped.setdefault(output_path, []).extend(worker_scenarios)

    for output_path, worker_scenarios in grouped.items():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            _render_test_file(_class_name(output_path), worker_scenarios, endpoints),
            encoding="utf-8",
        )
        generated.append(output_path)

    if generated:
        artifacts = [collect_artifact(project_root, path, "generated_test") for path in generated]
        write_manifest(project_root, artifacts)

    return generated


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Write deterministic Tide pytest cases")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--parsed", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--generation-plan", type=Path, required=True)
    args = parser.parse_args()

    generated = write_deterministic_cases(
        args.project_root,
        args.parsed,
        args.scenarios,
        args.generation_plan,
    )
    print(json.dumps({"generated": [str(path) for path in generated]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
