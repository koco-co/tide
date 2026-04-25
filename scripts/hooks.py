"""插件 Hook 系统 — 参考 qa-flow 的 hook 架构，支持在 Wave 管道各阶段注入自定义处理。"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import StrEnum


class HookPoint(StrEnum):
    """可用的 Hook 注册点。"""
    WAVE1_PARSE_BEFORE = "wave1:parse:before"
    WAVE1_PARSE_AFTER = "wave1:parse:after"
    WAVE2_ANALYZE_BEFORE = "wave2:analyze:before"
    WAVE2_ANALYZE_AFTER = "wave2:analyze:after"
    WAVE3_GENERATE_BEFORE = "wave3:generate:before"
    WAVE3_GENERATE_AFTER = "wave3:generate:after"
    WAVE4_REVIEW_BEFORE = "wave4:review:before"
    WAVE4_REVIEW_AFTER = "wave4:review:after"
    OUTPUT_NOTIFY = "output:notify"


@dataclass(frozen=True)
class HookRegistration:
    """单个 Hook 的注册信息。"""
    point: HookPoint
    name: str
    command: str
    description: str = ""
    env_required: list[str] = field(default_factory=list)


@dataclass
class HookRegistry:
    """Hook 注册表 — 管理已注册的 Hook 及其执行。"""
    _hooks: dict[HookPoint, list[HookRegistration]] = field(default_factory=dict)

    def register(self, hook: HookRegistration) -> None:
        """注册一个 Hook。"""
        if hook.point not in self._hooks:
            self._hooks[hook.point] = []
        self._hooks[hook.point] = [*self._hooks[hook.point], hook]

    def get_hooks(self, point: HookPoint) -> list[HookRegistration]:
        """获取指定 Hook 点的所有注册。"""
        return list(self._hooks.get(point, []))

    def has_hooks(self, point: HookPoint) -> bool:
        """检查指定 Hook 点是否有注册。"""
        return bool(self._hooks.get(point))

    @property
    def all_points(self) -> list[HookPoint]:
        """返回所有已注册的 Hook 点。"""
        return sorted(self._hooks.keys())


def load_hooks_from_config(config_path: str) -> HookRegistry:
    """从 YAML 配置文件加载 Hook 注册。

    配置格式:
    ```yaml
    hooks:
      - point: wave1:parse:after
        name: custom-filter
        command: python scripts/custom_filter.py
        description: 自定义过滤规则
        env_required: []
    ```
    """
    from pathlib import Path

    import yaml

    registry = HookRegistry()
    path = Path(config_path)

    if not path.exists():
        return registry

    try:
        config = yaml.safe_load(path.read_text())
        if config is None:
            return registry

        for hook_data in config.get("hooks", []):
            point_str = hook_data.get("point", "")
            try:
                point = HookPoint(point_str)
            except ValueError:
                print(
                    f"[hooks] Warning: unknown hook point '{point_str}', skipping",
                    file=sys.stderr,
                )
                continue

            registration = HookRegistration(
                point=point,
                name=hook_data.get("name", "unnamed"),
                command=hook_data.get("command", ""),
                description=hook_data.get("description", ""),
                env_required=hook_data.get("env_required", []),
            )
            registry.register(registration)
    except Exception as exc:
        print(f"[hooks] Warning: failed to load hooks config: {exc}", file=sys.stderr)

    return registry


def run_hook(point_str: str, project_root: str = ".") -> None:
    """根据 YAML 配置执行指定 hook point 的所有注册命令。"""
    import subprocess
    from pathlib import Path

    config_path = Path(project_root) / "tide-config.yaml"
    registry = load_hooks_from_config(str(config_path))

    try:
        point = HookPoint(point_str)
    except ValueError:
        print(f"[hooks] Unknown hook point: {point_str}")
        return

    registrations = registry.get_hooks(point)
    if not registrations:
        print(f"[hooks] No hooks registered for {point_str}")
        return

    for reg in registrations:
        print(f"[hooks] Running {reg.name} for {point_str}...")
        result = subprocess.run(reg.command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[hooks] {reg.name} failed: {result.stderr.strip()}")
        else:
            print(f"[hooks] {reg.name} OK")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tide Hooks CLI")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run")
    run_p.add_argument("point", help="Hook point name (e.g. wave1:parse:after)")
    run_p.add_argument("--project-root", default=".")

    args = parser.parse_args()

    if args.command == "run":
        run_hook(args.point, args.project_root)
