"""Tide run context parsing and path boundary helpers."""

from __future__ import annotations

import argparse
import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TideArguments:
    har_path: Path
    quick: bool = False
    yes: bool = False
    non_interactive: bool = False
    resume: bool = False
    wave: int | None = None

    @property
    def requires_confirmation(self) -> bool:
        return not (self.quick or self.yes or self.non_interactive)


@dataclass(frozen=True)
class TideRunContext:
    project_root: Path
    plugin_dir: Path
    tide_dir: Path
    har_path: Path
    args: TideArguments


def parse_tide_arguments(argument_text: str) -> TideArguments:
    parser = argparse.ArgumentParser(prog="/tide", add_help=False)
    parser.add_argument("har_path")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--yes", "-y", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--wave", type=int)

    namespace, _unknown = parser.parse_known_args(shlex.split(argument_text))
    return TideArguments(
        har_path=Path(namespace.har_path).expanduser().resolve(),
        quick=namespace.quick,
        yes=namespace.yes,
        non_interactive=namespace.non_interactive,
        resume=namespace.resume,
        wave=namespace.wave,
    )


def resolve_run_context(
    argument_text: str,
    project_root: Path,
    plugin_dir: Path,
) -> TideRunContext:
    args = parse_tide_arguments(argument_text)
    resolved_project = project_root.expanduser().resolve()
    resolved_plugin = plugin_dir.expanduser().resolve()
    return TideRunContext(
        project_root=resolved_project,
        plugin_dir=resolved_plugin,
        tide_dir=resolved_project / ".tide",
        har_path=args.har_path,
        args=args,
    )
