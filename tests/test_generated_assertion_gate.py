"""Tests for generated Tide assertion hard gates."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.generated_assertion_gate import validate_generated_assertions


def _write_generated(path: Path, scenario_id: str, extra: str = "") -> None:
    path.write_text(
        "class TestGenerated:\n"
        '    """Generated."""\n\n'
        "    def test_generated(self):\n"
        f'        """{scenario_id}"""\n'
        '        assert response["status_code"] == 200, "L1 status contract changed"\n'
        '        assert isinstance(body, dict), "L2 response body contract must be a dict"\n'
        '        assert body["code"] == 1, "L3 business code contract changed"\n'
        f"{extra}",
        encoding="utf-8",
    )


def test_validate_generated_assertions_requires_l4_when_scenario_has_l4(tmp_path: Path) -> None:
    scenarios = tmp_path / "scenarios.json"
    generated = tmp_path / "test_generated.py"
    scenarios.write_text(
        json.dumps({
            "scenarios": [
                {
                    "scenario_id": "write_case",
                    "confidence": "high",
                    "assertion_plan": {"L4": {"table": "metadata_sync_task"}},
                }
            ]
        }),
        encoding="utf-8",
    )
    _write_generated(generated, "write_case")

    result = validate_generated_assertions(scenarios, [generated])

    assert not result.ok
    assert any("missing L4" in violation for violation in result.violations)


def test_validate_generated_assertions_accepts_real_l4_and_l5_markers(tmp_path: Path) -> None:
    scenarios = tmp_path / "scenarios.json"
    generated = tmp_path / "test_generated.py"
    scenarios.write_text(
        json.dumps({
            "scenarios": [
                {
                    "scenario_id": "chain_case",
                    "type": "e2e_chain",
                    "confidence": "high",
                    "assertion_plan": {
                        "L4": {"field_detail": ["data is not None"]},
                        "L5": [{"description": "metadata links to datamap"}],
                    },
                }
            ]
        }),
        encoding="utf-8",
    )
    _write_generated(
        generated,
        "chain_case",
        '        assert db_row is not None, "L4 persistence contract changed"\n'
        '        assert linked_result["id"] == created_id, "L5 linkage contract changed"\n',
    )

    result = validate_generated_assertions(scenarios, [generated])

    assert result.ok
    assert result.violations == []


def test_validate_generated_assertions_rejects_empty_l4_l5_plans(tmp_path: Path) -> None:
    scenarios = tmp_path / "scenarios.json"
    generated = tmp_path / "test_generated.py"
    scenarios.write_text(
        json.dumps({
            "scenarios": [
                {
                    "scenario_id": "empty_plan_case",
                    "confidence": "high",
                    "assertion_plan": {
                        "L4": {"db_verify": []},
                        "L5": {"ui_verify": []},
                    },
                }
            ]
        }),
        encoding="utf-8",
    )
    _write_generated(generated, "empty_plan_case")

    result = validate_generated_assertions(scenarios, [generated])

    assert not result.ok
    assert "empty_plan_case: empty L4 plan" in result.violations
    assert "empty_plan_case: empty L5 plan" in result.violations
