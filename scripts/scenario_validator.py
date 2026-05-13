"""Validate Tide scenario and generation-plan outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_scenario_outputs(
    parsed_path: Path,
    scenarios_path: Path,
    generation_plan_path: Path,
) -> dict[str, Any]:
    parsed = _read_json(parsed_path)
    scenarios_doc = _read_json(scenarios_path)
    plan = _read_json(generation_plan_path)

    endpoint_ids = {item["id"] for item in parsed.get("endpoints", []) if item.get("id")}
    scenarios = scenarios_doc.get("scenarios", [])
    scenario_id_list = [item["scenario_id"] for item in scenarios if item.get("scenario_id")]
    scenario_ids = set(scenario_id_list)

    if not scenarios:
        raise ValueError("scenarios.json contains no scenarios")
    if len(scenario_id_list) != len(scenario_ids):
        raise ValueError("duplicate scenario_id found")

    for scenario in scenarios:
        endpoint_id = scenario.get("endpoint_id")
        if endpoint_id and endpoint_id not in endpoint_ids:
            raise ValueError(f"unknown endpoint_id: {endpoint_id}")

    medium_or_high_count = sum(
        1 for scenario in scenarios
        if scenario.get("confidence") in {"medium", "high"}
    )
    medium_or_high_ratio = medium_or_high_count / len(scenarios)
    if medium_or_high_ratio < 0.60:
        raise ValueError(
            f"confidence>=medium ratio below 60%: {medium_or_high_count}/{len(scenarios)}"
        )

    for endpoint_id in endpoint_ids:
        has_har_direct = any(
            s.get("endpoint_id") == endpoint_id and s.get("type") == "har_direct"
            for s in scenarios
        )
        if not has_har_direct:
            raise ValueError(f"endpoint {endpoint_id} has no har_direct scenario")

    workers = plan.get("workers", [])
    if not workers:
        raise ValueError("generation-plan.json contains no workers")
    for worker in workers:
        for scenario_id in worker.get("scenario_ids", []):
            if scenario_id not in scenario_ids:
                raise ValueError(f"unknown scenario_id in generation plan: {scenario_id}")

    return {
        "ok": True,
        "endpoint_count": len(endpoint_ids),
        "scenario_count": len(scenarios),
        "confidence_medium_or_high_count": medium_or_high_count,
        "confidence_medium_or_high_ratio": medium_or_high_ratio,
        "worker_count": len(workers),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Validate Tide scenario outputs")
    parser.add_argument("--parsed", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--generation-plan", type=Path, required=True)
    args = parser.parse_args()

    report = validate_scenario_outputs(args.parsed, args.scenarios, args.generation_plan)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
