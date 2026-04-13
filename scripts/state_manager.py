"""sisyphus-autoflow 会话的波次检查点状态管理器。"""

import shutil
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from scripts.common import AUTOFLOW_DIR

# ---------------------------------------------------------------------------
# 枚举与模型定义
# ---------------------------------------------------------------------------


class WaveStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class WaveState(BaseModel):
    status: WaveStatus = WaveStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    agents: list[str] = []
    data: dict = {}


class UserConfirmation(BaseModel):
    confirmed: bool = False
    modifications: list[str] = []
    confirmed_at: str | None = None


class SessionState(BaseModel):
    session_id: str
    source_har: str
    current_wave: int = 0
    waves: dict[str, WaveState] = {}
    user_confirmations: dict[str, UserConfirmation] = {}


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _state_dir(project_root: Path) -> Path:
    return project_root / AUTOFLOW_DIR


def _state_file(project_root: Path) -> Path:
    return _state_dir(project_root) / "state.json"


def _read_state(project_root: Path) -> SessionState | None:
    path = _state_file(project_root)
    if not path.exists():
        return None
    try:
        return SessionState.model_validate_json(path.read_text())
    except Exception as exc:
        raise ValueError(f"Failed to read state file: {exc}") from exc


def _write_state(project_root: Path, state: SessionState) -> None:
    path = _state_file(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2))


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def init_session(project_root: Path, har_filename: str) -> SessionState:
    """创建包含 4 个待执行波次的新 autoflow 会话。

    Raises:
        ValueError: 若 project_root 中已存在会话。
    """
    state_dir = _state_dir(project_root)
    state_dir.mkdir(parents=True, exist_ok=True)

    if _state_file(project_root).exists():
        raise ValueError("existing session found — archive or remove it first")

    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    session_id = f"af_{timestamp}"

    waves: dict[str, WaveState] = {
        "1": WaveState(),
        "2": WaveState(),
        "3": WaveState(),
        "4": WaveState(),
    }

    state = SessionState(
        session_id=session_id,
        source_har=har_filename,
        waves=waves,
    )

    _write_state(project_root, state)
    return state


def advance_wave(
    project_root: Path,
    wave: int,
    data: dict | None = None,
) -> SessionState:
    """将会话推进到下一个波次，并将当前波次标记为已完成。

    Args:
        project_root: 包含 .autoflow/ 的根目录。
        wave: 要完成的波次编号（必须等于 current_wave + 1）。
        data: 可选的结果数据，用于与波次一同存储。

    Raises:
        ValueError: 若不存在会话或波次顺序有误。
    """
    state = _read_state(project_root)
    if state is None:
        raise ValueError("No active session found")

    expected = state.current_wave + 1
    if wave != expected:
        raise ValueError(
            f"Wave {wave} is out of order — expected wave {expected}"
        )

    completed_wave = state.waves[str(wave)].model_copy(
        update={
            "status": WaveStatus.COMPLETED,
            "completed_at": _now_iso(),
            "data": data or {},
        }
    )

    updated_waves = {**state.waves, str(wave): completed_wave}

    new_state = state.model_copy(
        update={
            "current_wave": wave,
            "waves": updated_waves,
        }
    )

    _write_state(project_root, new_state)
    return new_state


def resume_session(project_root: Path) -> SessionState | None:
    """加载并返回当前会话状态，若无会话则返回 None。"""
    return _read_state(project_root)


def archive_session(project_root: Path) -> Path | None:
    """将所有 .autoflow 文件（history/ 除外）移动到 .autoflow/history/{session_id}/。

    Returns:
        历史目录路径，若无活跃会话则返回 None。
    """
    state = _read_state(project_root)
    if state is None:
        return None

    state_dir = _state_dir(project_root)
    history_dir = state_dir / "history" / state.session_id
    history_dir.mkdir(parents=True, exist_ok=True)

    for item in state_dir.iterdir():
        if item.name == "history":
            continue
        shutil.move(str(item), str(history_dir / item.name))

    return history_dir


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="AutoFlow state manager")
    sub = parser.add_subparsers(dest="command")

    init_p = sub.add_parser("init")
    init_p.add_argument("--har", required=True)
    init_p.add_argument("--project-root", default=".")

    advance_p = sub.add_parser("advance_wave")
    advance_p.add_argument("--wave", type=int, required=True)
    advance_p.add_argument("--project-root", default=".")

    archive_p = sub.add_parser("archive")
    archive_p.add_argument("--project-root", default=".")

    args = parser.parse_args()
    root = Path(args.project_root)

    if args.command == "init":
        try:
            state = init_session(root, args.har)
            print(f"Session initialized: {state.session_id}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "advance_wave":
        try:
            state = advance_wave(root, args.wave)
            print(f"Advanced to wave {args.wave}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "archive":
        result = archive_session(root)
        if result:
            print(f"Archived to {result}")
        else:
            print("No active session to archive")
    else:
        parser.print_help()
