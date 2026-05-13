#!/usr/bin/env python3
"""Live Execution Gate: check if generated tests make real HTTP calls.

Writes .tide/live-gate-result.json with test_mode field.
If DETERMINISTIC, also writes .tide/skip-wave4.txt so Wave 4 is skipped.
Exit code 0 = gate passed, 1 = blocked.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def detect_test_mode(generated_files: list[Path]) -> str:
    """Scan generated test files for real HTTP client usage.

    Returns 'LIVE' if any file uses requests, httpx, self.req, session.get/post/put/delete,
    or .request(). Returns 'DETERMINISTIC' otherwise.
    """
    live_patterns = [
        re.compile(r"requests\."),
        re.compile(r"httpx\."),
        re.compile(r"self\.req"),
        re.compile(r"session\.(get|post|put|delete)"),
        re.compile(r"\.request\("),
    ]

    for f in generated_files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for pattern in live_patterns:
            if pattern.search(text):
                return "LIVE"

    return "DETERMINISTIC"


def find_generated_files(project_root: Path) -> list[Path]:
    """Find tide_generated_* test files in the project."""
    results = []
    for py_file in project_root.rglob("tide_generated_*.py"):
        results.append(py_file)
    return sorted(results)


def main() -> int:
    parser = argparse.ArgumentParser(description="Live Execution Gate")
    parser.add_argument("--project-root", required=True, help="Project root directory")
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Specific files to check (auto-discovers if not provided)",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    tide_dir = project_root / ".tide"
    tide_dir.mkdir(parents=True, exist_ok=True)

    if args.files:
        generated_files = [Path(f).resolve() for f in args.files]
    else:
        generated_files = find_generated_files(project_root)

    if not generated_files:
        print("NO_GENERATED_FILES: no tide_generated_*.py files found")
        result = {"test_mode": "NO_FILES", "files_checked": []}
        (tide_dir / "live-gate-result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return 1

    test_mode = detect_test_mode(generated_files)
    file_list = [str(f.relative_to(project_root)) for f in generated_files]

    print(f"TEST_MODE={test_mode}")
    print(f"Files checked: {len(generated_files)}")
    for f in file_list:
        print(f"  {f}")

    result = {
        "test_mode": test_mode,
        "files_checked": file_list,
    }
    (tide_dir / "live-gate-result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if test_mode == "LIVE":
        print("Gate: PASS (LIVE) - real HTTP calls detected")
        # Remove skip file if it exists (from a previous run)
        skip_file = tide_dir / "skip-wave4.txt"
        if skip_file.exists():
            skip_file.unlink()
        return 0
    else:
        print("Gate: FAIL (DETERMINISTIC) - no real HTTP calls detected")
        print("Writing skip-wave4.txt to block Wave 4 execution")
        (tide_dir / "skip-wave4.txt").write_text(
            f"DETERMINISTIC_SKELETON: no real HTTP calls in {len(generated_files)} generated files\n",
            encoding="utf-8",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
