"""Tests for deterministic scenario artifact normalization."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.scenario_normalizer import normalize_scenario_artifacts
from scripts.scenario_validator import validate_scenario_outputs


def test_normalize_scenario_artifacts_repairs_duplicate_ids_and_plan(tmp_path: Path) -> None:
    parsed = tmp_path / "parsed.json"
    scenarios = tmp_path / "scenarios.json"
    plan = tmp_path / "generation-plan.json"

    parsed.write_text(
        json.dumps({
            "endpoints": [
                {"id": "ep1", "method": "POST", "path": "/dmetadata/v1/syncTask/pageTask"}
            ]
        }),
        encoding="utf-8",
    )
    scenarios.write_text(
        json.dumps({
            "scenarios": [
                {
                    "scenario_id": "syncTask_pageTask_boundary",
                    "endpoint": {"method": "POST", "path": "/dmetadata/v1/syncTask/pageTask"},
                    "type": "har_direct",
                    "confidence": "high",
                },
                {
                    "scenario_id": "syncTask_pageTask_boundary",
                    "endpoint": {"method": "POST", "path": "/dmetadata/v1/syncTask/pageTask"},
                    "type": "boundary",
                    "confidence": "medium",
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
                    "scenario_ids": ["syncTask_pageTask_boundary", "syncTask_pageTask_boundary"],
                    "output_file": "testcases/scenariotest/assets/meta_data/tide_generated_metadata_test.py",
                }
            ]
        }),
        encoding="utf-8",
    )

    report = normalize_scenario_artifacts(parsed, scenarios, plan)

    updated_scenarios = json.loads(scenarios.read_text(encoding="utf-8"))
    updated_plan = json.loads(plan.read_text(encoding="utf-8"))

    assert report["renamed"] == {"syncTask_pageTask_boundary": ["syncTask_pageTask_boundary_2"]}
    assert [item["scenario_id"] for item in updated_scenarios["scenarios"]] == [
        "syncTask_pageTask_boundary",
        "syncTask_pageTask_boundary_2",
    ]
    assert [item["endpoint_id"] for item in updated_scenarios["scenarios"]] == ["ep1", "ep1"]
    assert updated_plan["workers"][0]["scenario_ids"] == [
        "syncTask_pageTask_boundary",
        "syncTask_pageTask_boundary_2",
    ]

    validation = validate_scenario_outputs(parsed, scenarios, plan)
    assert validation["ok"] is True
