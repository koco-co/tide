"""Validate generated tests against Tide scenario assertion hard gates."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AssertionGateResult:
    ok: bool
    checked_scenarios: int
    generated_tests: int
    violations: list[str]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _has_plan(assertion_plan: dict[str, Any], level: str) -> bool:
    value = assertion_plan.get(level)
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def _requires_l5(scenario: dict[str, Any], assertion_plan: dict[str, Any]) -> bool:
    scenario_type = str(scenario.get("type") or "")
    return _has_plan(assertion_plan, "L5") or scenario_type in {"e2e_chain", "linkage", "chain"}


def _function_source(path: Path, node: ast.FunctionDef) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    end_lineno = node.end_lineno or node.lineno
    return "\n".join(lines[node.lineno - 1:end_lineno])


def _generated_test_levels(generated_files: list[Path]) -> dict[str, set[str]]:
    tests: dict[str, set[str]] = {}
    for path in generated_files:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            scenario_id = ast.get_docstring(node) or node.name.removeprefix("test_")
            source = _function_source(path, node)
            levels = {
                level
                for level in ("L1", "L2", "L3", "L4", "L5")
                if level in source
            }
            tests[scenario_id] = levels
    return tests


def validate_generated_assertions(scenarios_path: Path, generated_files: list[Path]) -> AssertionGateResult:
    scenarios_doc = _read_json(scenarios_path)
    scenarios = [
        scenario
        for scenario in scenarios_doc.get("scenarios", [])
        if isinstance(scenario, dict) and scenario.get("scenario_id")
    ]
    generated_tests = _generated_test_levels(generated_files)
    violations: list[str] = []

    for scenario in scenarios:
        scenario_id = str(scenario["scenario_id"])
        levels = generated_tests.get(scenario_id)
        if levels is None:
            violations.append(f"{scenario_id}: missing generated test")
            continue

        for level in ("L1", "L2", "L3"):
            if level not in levels:
                violations.append(f"{scenario_id}: missing {level}")

        assertion_plan = scenario.get("assertion_plan")
        if not isinstance(assertion_plan, dict):
            assertion_plan = {}
        if _has_plan(assertion_plan, "L4") and "L4" not in levels:
            violations.append(f"{scenario_id}: missing L4")
        if _requires_l5(scenario, assertion_plan) and "L5" not in levels:
            violations.append(f"{scenario_id}: missing L5")

    return AssertionGateResult(
        ok=not violations,
        checked_scenarios=len(scenarios),
        generated_tests=len(generated_tests),
        violations=violations,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Tide generated assertion coverage")
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("generated_files", type=Path, nargs="+")
    args = parser.parse_args()

    result = validate_generated_assertions(args.scenarios, args.generated_files)
    print(json.dumps({
        "ok": result.ok,
        "checked_scenarios": result.checked_scenarios,
        "generated_tests": result.generated_tests,
        "violations": result.violations,
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
