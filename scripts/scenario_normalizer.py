"""Normalize Tide scenario artifacts before test generation."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _endpoint_lookup(parsed: dict[str, Any]) -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}
    for endpoint in parsed.get("endpoints", []):
        method = str(endpoint.get("method", "")).upper()
        path = str(endpoint.get("path", ""))
        endpoint_id = endpoint.get("id")
        if method and path and endpoint_id:
            lookup[(method, path)] = str(endpoint_id)
    return lookup


def _attach_endpoint_id(scenario: dict[str, Any], lookup: dict[tuple[str, str], str]) -> None:
    if scenario.get("endpoint_id"):
        return
    endpoint = scenario.get("endpoint")
    if not isinstance(endpoint, dict):
        return
    method = str(endpoint.get("method", "")).upper()
    path = str(endpoint.get("path", ""))
    endpoint_id = lookup.get((method, path))
    if endpoint_id:
        scenario["endpoint_id"] = endpoint_id


def _ensure_confidence(scenario: dict[str, Any]) -> None:
    if scenario.get("confidence") in {"low", "medium", "high"}:
        return
    scenario["confidence"] = "medium"
    scenario.setdefault(
        "confidence_reason",
        "Deterministic fallback assigned medium confidence because source scenario omitted confidence.",
    )


def _ensure_type(scenario: dict[str, Any]) -> None:
    if scenario.get("type"):
        return
    scenario["type"] = "har_direct"
    scenario.setdefault(
        "type_reason",
        "Deterministic fallback assigned har_direct because source scenario omitted type.",
    )


def _rewrite_duplicate_ids(scenarios: list[dict[str, Any]]) -> tuple[dict[str, deque[str]], dict[str, list[str]]]:
    seen: defaultdict[str, int] = defaultdict(int)
    replacement_queues: dict[str, deque[str]] = defaultdict(deque)
    renamed: dict[str, list[str]] = {}

    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id", "")).strip()
        if not scenario_id:
            continue
        seen[scenario_id] += 1
        if seen[scenario_id] == 1:
            replacement_queues[scenario_id].append(scenario_id)
            continue

        new_id = f"{scenario_id}_{seen[scenario_id]}"
        scenario["scenario_id"] = new_id
        replacement_queues[scenario_id].append(new_id)
        renamed.setdefault(scenario_id, []).append(new_id)

    return replacement_queues, renamed


def _rewrite_generation_plan(plan: dict[str, Any], replacement_queues: dict[str, deque[str]]) -> None:
    for worker in plan.get("workers", []):
        rewritten: list[str] = []
        for scenario_id in worker.get("scenario_ids", []):
            queue = replacement_queues.get(str(scenario_id))
            if queue:
                rewritten.append(queue.popleft())
            else:
                rewritten.append(str(scenario_id))
        worker["scenario_ids"] = rewritten


def normalize_scenario_artifacts(
    parsed_path: Path,
    scenarios_path: Path,
    generation_plan_path: Path,
) -> dict[str, Any]:
    """Normalize scenario IDs and generation-plan references in place."""

    parsed = _read_json(parsed_path)
    scenarios_doc = _read_json(scenarios_path)
    plan = _read_json(generation_plan_path)

    scenarios = scenarios_doc.get("scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError("scenarios.json field 'scenarios' must be a list")

    lookup = _endpoint_lookup(parsed)
    for scenario in scenarios:
        if isinstance(scenario, dict):
            _attach_endpoint_id(scenario, lookup)
            _ensure_confidence(scenario)
            _ensure_type(scenario)

    replacement_queues, renamed = _rewrite_duplicate_ids(scenarios)
    _rewrite_generation_plan(plan, replacement_queues)

    _write_json(scenarios_path, scenarios_doc)
    _write_json(generation_plan_path, plan)

    return {
        "ok": True,
        "scenario_count": len(scenarios),
        "renamed": renamed,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Normalize Tide scenario artifacts")
    parser.add_argument("--parsed", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--generation-plan", type=Path, required=True)
    args = parser.parse_args()

    report = normalize_scenario_artifacts(args.parsed, args.scenarios, args.generation_plan)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
