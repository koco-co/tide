"""Tests for state manager - written first (TDD RED phase)."""

from pathlib import Path

import pytest

from scripts.state_manager import (
    WaveStatus,
    advance_wave,
    archive_session,
    init_session,
    resume_session,
)

# ---------------------------------------------------------------------------
# TestInitSession
# ---------------------------------------------------------------------------


class TestInitSession:
    def test_creates_state_file(self, tmp_path: Path) -> None:
        """init_session 在项目根目录下创建 .autoflow/state.json。"""
        init_session(tmp_path, "test.har")
        state_file = tmp_path / ".autoflow" / "state.json"
        assert state_file.exists()

    def test_state_has_session_id(self, tmp_path: Path) -> None:
        """session_id 以 'af_' 开头。"""
        state = init_session(tmp_path, "test.har")
        assert state.session_id.startswith("af_")

    def test_initial_wave_is_zero(self, tmp_path: Path) -> None:
        """current_wave == 0 且全部 4 个波次均为 PENDING 状态。"""
        state = init_session(tmp_path, "test.har")
        assert state.current_wave == 0
        assert len(state.waves) == 4
        for key in ("1", "2", "3", "4"):
            assert key in state.waves
            assert state.waves[key].status == WaveStatus.PENDING

    def test_raises_on_existing_session(self, tmp_path: Path) -> None:
        """第二次调用 init_session 应抛出包含 'existing session' 的 ValueError。"""
        init_session(tmp_path, "test.har")
        with pytest.raises(ValueError, match="existing session"):
            init_session(tmp_path, "test.har")


# ---------------------------------------------------------------------------
# TestAdvanceWave
# ---------------------------------------------------------------------------


class TestAdvanceWave:
    def test_advances_to_next_wave(self, tmp_path: Path) -> None:
        """初始化后，advance_wave(1) 应将 current_wave 设为 1 并将波次 '1' 标记为 COMPLETED。"""
        init_session(tmp_path, "test.har")
        data = {"agents": ["agent_a"], "results": "ok"}
        state = advance_wave(tmp_path, 1, data=data)

        assert state.current_wave == 1
        assert state.waves["1"].status == WaveStatus.COMPLETED
        assert state.waves["1"].completed_at is not None
        assert state.waves["1"].data == data

    def test_raises_on_out_of_order(self, tmp_path: Path) -> None:
        """初始化后（current_wave=0），advance_wave(3) 应抛出包含 'out of order' 的 ValueError。"""
        init_session(tmp_path, "test.har")
        with pytest.raises(ValueError, match="out of order"):
            advance_wave(tmp_path, 3)

    def test_cannot_skip_waves(self, tmp_path: Path) -> None:
        """不能跳过波次，wave 2 在 wave 1 完成前应拒绝。"""
        init_session(tmp_path, "test.har")
        with pytest.raises(ValueError, match="out of order"):
            advance_wave(tmp_path, 2)

    def test_sequential_wave_progression(self, tmp_path: Path) -> None:
        """按顺序推进全部 4 个波次。"""
        init_session(tmp_path, "test.har")
        for wave in range(1, 5):
            state = advance_wave(tmp_path, wave)
            assert state.current_wave == wave
            assert state.waves[str(wave)].status == WaveStatus.COMPLETED

    def test_advance_without_session_raises(self, tmp_path: Path) -> None:
        """无活跃会话时 advance_wave 应抛出 ValueError。"""
        with pytest.raises(ValueError, match="No active session"):
            advance_wave(tmp_path, 1)


# ---------------------------------------------------------------------------
# TestResumeSession
# ---------------------------------------------------------------------------


class TestResumeSession:
    def test_returns_state(self, tmp_path: Path) -> None:
        """初始化并推进波次 1 后，resume 应返回 current_wave=1 的状态。"""
        init_session(tmp_path, "test.har")
        advance_wave(tmp_path, 1)
        state = resume_session(tmp_path)

        assert state is not None
        assert state.current_wave == 1

    def test_returns_none_when_no_session(self, tmp_path: Path) -> None:
        """当 state.json 不存在时，resume 应返回 None。"""
        result = resume_session(tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# TestArchiveSession
# ---------------------------------------------------------------------------


class TestArchiveSession:
    def test_moves_to_history(self, tmp_path: Path) -> None:
        """完整运行（init + 4 次推进）后，archive 应将文件移动到 history/{session_id}/。"""
        state = init_session(tmp_path, "test.har")
        session_id = state.session_id

        for wave_num in range(1, 5):
            advance_wave(tmp_path, wave_num)

        history_dir = archive_session(tmp_path)

        assert history_dir is not None
        assert history_dir == tmp_path / ".autoflow" / "history" / session_id
        assert history_dir.exists()
        # state.json 应已移动到 history 目录
        assert (history_dir / "state.json").exists()
        # state.json 不应再存在于原始位置
        assert not (tmp_path / ".autoflow" / "state.json").exists()

    def test_archive_returns_none_without_session(self, tmp_path: Path) -> None:
        """无活跃会话时 archive 应返回 None。"""
        result = archive_session(tmp_path)
        assert result is None

    def test_archive_preserves_history_dir(self, tmp_path: Path) -> None:
        """归档不应移动 history/ 目录本身。"""
        init_session(tmp_path, "test.har")
        advance_wave(tmp_path, 1)
        archive_session(tmp_path)
        # history 目录应仍然存在
        assert (tmp_path / ".autoflow" / "history").is_dir()
