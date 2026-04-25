"""偏好学习系统 — 参考 qa-flow 的 preferences/ 架构，跨会话持久化用户偏好。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from pathlib import Path

from scripts.common import AUTOFLOW_DIR


class AutoflowPreferences(BaseModel):
    """用户偏好配置 — 从历史运行中学习。"""
    assertion_verbosity: str = "normal"  # terse | normal | verbose
    preferred_fixture_scope: str = "function"  # function | class | session | module
    allure_step_usage: bool = True
    code_style_line_length: int = 120
    db_assertion_enabled: bool = False
    skip_user_confirmation: bool = False
    industry: str = ""  # finance | healthcare | ecommerce | saas | ""


_PREFERENCES_FILE = "preferences.json"


def _preferences_path(project_root: Path) -> Path:
    return project_root / AUTOFLOW_DIR / _PREFERENCES_FILE


def load_preferences(project_root: Path) -> AutoflowPreferences:
    """加载偏好配置；若不存在则返回默认值。"""
    path = _preferences_path(project_root)
    if not path.exists():
        return AutoflowPreferences()
    try:
        return AutoflowPreferences.model_validate_json(path.read_text())
    except Exception:
        return AutoflowPreferences()


def save_preferences(project_root: Path, prefs: AutoflowPreferences) -> None:
    """保存偏好配置。"""
    path = _preferences_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prefs.model_dump_json(indent=2))


def update_preferences(
    project_root: Path,
    **updates: str | int | bool,
) -> AutoflowPreferences:
    """部分更新偏好配置（不可变方式）。"""
    current = load_preferences(project_root)
    updated = current.model_copy(update=updates)
    save_preferences(project_root, updated)
    return updated


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="AutoFlow preferences manager")
    sub = parser.add_subparsers(dest="command")

    read_p = sub.add_parser("read")
    read_p.add_argument("--key", help="Specific preference key to read")
    read_p.add_argument("--project-root", default=".")

    write_p = sub.add_parser("write")
    write_p.add_argument("--key", required=True)
    write_p.add_argument("--value", required=True)
    write_p.add_argument("--project-root", default=".")

    args = parser.parse_args()
    root = Path(args.project_root)

    if args.command == "read":
        prefs = load_preferences(root)
        if args.key:
            val = getattr(prefs, args.key, None)
            if val is not None:
                print(val)
            else:
                print(f"Unknown key: {args.key}", file=sys.stderr)
                sys.exit(1)
        else:
            print(prefs.model_dump_json(indent=2))
    elif args.command == "write":
        raw: str = args.value
        if raw.lower() == "true":
            value = True
        elif raw.lower() == "false":
            value = False
        elif raw.isdigit():
            value = int(raw)
        else:
            value = raw
        update_preferences(root, **{args.key: value})
        print(f"Set {args.key} = {value}")
    else:
        parser.print_help()
