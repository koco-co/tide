"""Tests for deterministic Tide pytest generation."""

from __future__ import annotations

import json
import py_compile
from pathlib import Path

from scripts.deterministic_case_writer import write_deterministic_cases
from scripts.format_checker import check_file
from scripts.generated_assertion_gate import validate_generated_assertions


def test_write_deterministic_cases_creates_collectable_l1_to_l5_tests(tmp_path: Path) -> None:
    parsed = tmp_path / ".tide" / "parsed.json"
    scenarios = tmp_path / ".tide" / "scenarios.json"
    plan = tmp_path / ".tide" / "generation-plan.json"
    parsed.parent.mkdir()

    endpoint = {
        "id": "ep1",
        "method": "POST",
        "path": "/dmetadata/v1/syncTask/pageTask",
        "response": {
            "status": 200,
            "body": {
                "code": 1,
                "success": True,
                "data": {
                    "pageNow": 1,
                    "pageSize": 20,
                    "total": 1,
                    "dataSourceId": "43",
                    "tableId": "12695",
                    "data": [],
                },
            },
        },
        "request": {
            "headers": [{"name": "Host", "value": "172.16.122.52"}],
            "body": {"pageNow": 1, "pageSize": 20},
        },
    }
    parsed.write_text(json.dumps({"endpoints": [endpoint]}), encoding="utf-8")
    scenarios.write_text(
        json.dumps({
            "scenarios": [
                {
                        "scenario_id": "sync_task_har_direct",
                        "endpoint_id": "ep1",
                        "type": "har_direct",
                        "confidence": "high",
                        "assertion_plan": {
                            "L1": {"expected_status": 200},
                            "L2": {"required_fields": ["pageNow", "pageSize", "total", "data", "success"]},
                            "L3": [{"field": "code", "expected": 1}],
                        },
                    },
                {
                    "scenario_id": "sync_task_write_boundary",
                    "endpoint_id": "ep1",
                    "type": "boundary",
                    "confidence": "medium",
                    "assertion_plan": {
                        "L4": [{"table": "metadata_sync_task", "operation": "INSERT"}],
                    },
                },
                {
                    "scenario_id": "metadata_to_datamap_e2e",
                    "endpoint_id": "ep1",
                    "type": "e2e_chain",
                    "confidence": "high",
                    "assertion_plan": {
                        "L5": [{"description": "taskId links sync job query"}],
                    },
                },
            ]
        }),
        encoding="utf-8",
    )
    plan.write_text(
        json.dumps({
            "workers": [
                {
                    "worker_id": "metadata",
                    "scenario_ids": [
                        "sync_task_har_direct",
                        "sync_task_write_boundary",
                        "metadata_to_datamap_e2e",
                    ],
                    "output_file": "testcases/scenariotest/assets/meta_data/tide_generated_metadata_test.py",
                }
            ]
        }),
        encoding="utf-8",
    )

    generated = write_deterministic_cases(tmp_path, parsed, scenarios, plan)

    assert generated == [tmp_path / "testcases/scenariotest/assets/meta_data/tide_generated_metadata_test.py"]
    output = generated[0].read_text(encoding="utf-8")
    py_compile.compile(str(generated[0]), doraise=True)

    assert "class TestTideGeneratedMetadata" in output
    assert "def test_sync_task_har_direct" in output
    assert "L1" in output
    assert "L2" in output
    assert "L3" in output
    assert "L4 data field must exist" in output
    assert "L5 code field must exist" in output
    assert "requires project-specific wiring" not in output
    assert "assert True, \"L4" not in output
    assert "assert True, \"L5" not in output
    assert "172.16.122.52" not in output
    assert "webhook" not in output.lower()
    assert "12695" not in output
    assert "dataSourceId" not in output
    assert (tmp_path / ".tide/artifact-manifest.json").exists()
    violations = check_file(str(generated[0]))
    assert not any(violation.rule.id == "FC11" for violation in violations)
    assert not any(violation.rule.id == "FC15" for violation in violations)
    assertion_result = validate_generated_assertions(scenarios, generated)
    assert assertion_result.ok, assertion_result.violations


def test_write_deterministic_cases_merges_workers_with_same_fallback_output(tmp_path: Path) -> None:
    parsed = tmp_path / ".tide" / "parsed.json"
    scenarios = tmp_path / ".tide" / "scenarios.json"
    plan = tmp_path / ".tide" / "generation-plan.json"
    parsed.parent.mkdir()

    parsed.write_text(
        json.dumps({
            "endpoints": [
                {"id": "ep1", "response": {"status": 200, "body": {"code": 1, "success": True}}},
                {"id": "ep2", "response": {"status": 200, "body": {"code": 1, "success": True}}},
            ]
        }),
        encoding="utf-8",
    )
    scenarios.write_text(
        json.dumps({
            "scenarios": [
                {"scenario_id": "metadata_case", "endpoint_id": "ep1", "type": "har_direct"},
                {"scenario_id": "assets_case", "endpoint_id": "ep2", "type": "har_direct"},
            ]
        }),
        encoding="utf-8",
    )
    plan.write_text(
        json.dumps({
            "workers": [
                {"worker_id": "metadata", "scenario_ids": ["metadata_case"], "output_file": "tests/interface/test_metadata.py"},
                {"worker_id": "assets", "scenario_ids": ["assets_case"], "output_file": "tests/interface/test_assets.py"},
            ]
        }),
        encoding="utf-8",
    )

    generated = write_deterministic_cases(tmp_path, parsed, scenarios, plan)

    assert generated == [tmp_path / "testcases/scenariotest/assets/meta_data/tide_generated_metadata_test.py"]
    output = generated[0].read_text(encoding="utf-8")
    assert "def test_metadata_case" in output
    assert "def test_assets_case" in output


def test_write_deterministic_cases_deduplicates_scenarios_across_workers(tmp_path: Path) -> None:
    parsed = tmp_path / ".tide" / "parsed.json"
    scenarios = tmp_path / ".tide" / "scenarios.json"
    plan = tmp_path / ".tide" / "generation-plan.json"
    parsed.parent.mkdir()

    parsed.write_text(
        json.dumps({
            "endpoints": [
                {"id": "ep1", "method": "POST", "path": "/dassets/v1/demo", "response": {"status": 200}},
                {"id": "ep2", "method": "POST", "path": "/dassets/v1/other", "response": {"status": 200}},
            ]
        }),
        encoding="utf-8",
    )
    scenarios.write_text(
        json.dumps({
            "scenarios": [
                {"scenario_id": "duplicate_case", "endpoint_id": "ep1", "type": "har_direct"},
                {"scenario_id": "unique_case", "endpoint_id": "ep2", "type": "har_direct"},
            ]
        }),
        encoding="utf-8",
    )
    plan.write_text(
        json.dumps({
            "workers": [
                {
                    "worker_id": "first",
                    "scenario_ids": ["duplicate_case", "duplicate_case"],
                    "output_file": "testcases/scenariotest/assets/first/tide_generated_first_test.py",
                },
                {
                    "worker_id": "second",
                    "scenario_ids": ["duplicate_case", "unique_case"],
                    "output_file": "testcases/scenariotest/assets/second/tide_generated_second_test.py",
                },
            ]
        }),
        encoding="utf-8",
    )

    generated = write_deterministic_cases(tmp_path, parsed, scenarios, plan)

    combined = "\n".join(path.read_text(encoding="utf-8") for path in generated)
    assert combined.count("def test_duplicate_case") == 1
    assert combined.count('"""duplicate_case"""') == 1
    assert combined.count("def test_unique_case") == 1


def test_write_deterministic_cases_writes_one_test_class_per_endpoint(tmp_path: Path) -> None:
    parsed = tmp_path / ".tide" / "parsed.json"
    scenarios = tmp_path / ".tide" / "scenarios.json"
    plan = tmp_path / ".tide" / "generation-plan.json"
    parsed.parent.mkdir()

    parsed.write_text(
        json.dumps({
            "endpoints": [
                {
                    "id": f"ep{index}",
                    "method": "POST",
                    "path": f"/dmetadata/v1/table/query{index}",
                    "response": {"status": 200, "body": {"code": 1}},
                }
                for index in range(16)
            ]
        }),
        encoding="utf-8",
    )
    scenario_docs = [
        {"scenario_id": f"metadata_case_{index}", "endpoint_id": f"ep{index}", "type": "har_direct"}
        for index in range(16)
    ]
    scenarios.write_text(json.dumps({"scenarios": scenario_docs}), encoding="utf-8")
    plan.write_text(
        json.dumps({
            "workers": [
                {
                    "worker_id": "metadata",
                    "scenario_ids": [scenario["scenario_id"] for scenario in scenario_docs],
                    "output_file": "testcases/scenariotest/assets/meta_data/tide_generated_metadata_test.py",
                }
            ]
        }),
        encoding="utf-8",
    )

    generated = write_deterministic_cases(tmp_path, parsed, scenarios, plan)
    output = generated[0].read_text(encoding="utf-8")

    assert output.count("class TestTideGeneratedMetadata") == 16
    assert "class TestTideGeneratedMetadataPostDmetadataV1TableQuery0:" in output
    assert "class TestTideGeneratedMetadataPostDmetadataV1TableQuery15:" in output
    assert "class TestTideGeneratedMetadata2:" not in output
    assert not any(violation.rule.id == "FC02" for violation in check_file(str(generated[0])))
