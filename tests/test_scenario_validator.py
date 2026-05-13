"""Tests for scenario_validator module."""

import json
from pathlib import Path

import pytest

from scripts.scenario_validator import validate_scenario_outputs


def test_validate_scenario_outputs_accepts_valid_files(tmp_path: Path) -> None:
    parsed = tmp_path / "parsed.json"
    scenarios = tmp_path / "scenarios.json"
    plan = tmp_path / "generation-plan.json"

    parsed.write_text(json.dumps({
        "endpoints": [{"id": "ep1", "method": "POST", "path": "/dassets/v1/datamap/queryDetail"}]
    }))
    scenarios.write_text(json.dumps({
        "scenarios": [
            {
                "scenario_id": "s1",
                "endpoint_id": "ep1",
                "type": "har_direct",
                "confidence": "high",
                "assertion_plan": {"L1": {"expected_status": 200}},
            }
        ]
    }))
    plan.write_text(json.dumps({
        "workers": [{"worker_id": "assets", "scenario_ids": ["s1"], "output_file": "tests/test_assets.py"}]
    }))

    report = validate_scenario_outputs(parsed, scenarios, plan)

    assert report["ok"] is True
    assert report["scenario_count"] == 1


def test_validate_scenario_outputs_rejects_unknown_endpoint(tmp_path: Path) -> None:
    parsed = tmp_path / "parsed.json"
    scenarios = tmp_path / "scenarios.json"
    plan = tmp_path / "generation-plan.json"

    parsed.write_text(json.dumps({"endpoints": [{"id": "ep1"}]}))
    scenarios.write_text(json.dumps({"scenarios": [{"scenario_id": "s1", "endpoint_id": "missing", "type": "har_direct"}]}))
    plan.write_text(json.dumps({"workers": [{"worker_id": "assets", "scenario_ids": ["s1"], "output_file": "tests/test_assets.py"}]}))

    with pytest.raises(ValueError, match="unknown endpoint_id"):
        validate_scenario_outputs(parsed, scenarios, plan)


def test_validate_scenario_outputs_rejects_duplicate_scenario_ids(tmp_path: Path) -> None:
    parsed = tmp_path / "parsed.json"
    scenarios = tmp_path / "scenarios.json"
    plan = tmp_path / "generation-plan.json"

    parsed.write_text(json.dumps({"endpoints": [{"id": "ep1"}]}))
    scenarios.write_text(json.dumps({
        "scenarios": [
            {"scenario_id": "s1", "endpoint_id": "ep1", "type": "har_direct", "confidence": "high"},
            {"scenario_id": "s1", "endpoint_id": "ep1", "type": "param_validation", "confidence": "medium"},
        ]
    }))
    plan.write_text(json.dumps({"workers": [{"worker_id": "assets", "scenario_ids": ["s1"], "output_file": "tests/test_assets.py"}]}))

    with pytest.raises(ValueError, match="duplicate scenario_id"):
        validate_scenario_outputs(parsed, scenarios, plan)


def test_validate_scenario_outputs_rejects_low_confidence_ratio(tmp_path: Path) -> None:
    parsed = tmp_path / "parsed.json"
    scenarios = tmp_path / "scenarios.json"
    plan = tmp_path / "generation-plan.json"

    parsed.write_text(json.dumps({"endpoints": [{"id": "ep1"}]}))
    scenarios.write_text(json.dumps({
        "scenarios": [
            {"scenario_id": "s1", "endpoint_id": "ep1", "type": "har_direct", "confidence": "low"},
            {"scenario_id": "s2", "endpoint_id": "ep1", "type": "param_validation"},
        ]
    }))
    plan.write_text(json.dumps({"workers": [{"worker_id": "assets", "scenario_ids": ["s1", "s2"], "output_file": "tests/test_assets.py"}]}))

    with pytest.raises(ValueError, match="confidence>=medium ratio"):
        validate_scenario_outputs(parsed, scenarios, plan)
