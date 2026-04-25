"""Integration test: HAR parse → state persist → resume → archive."""
from pathlib import Path

import pytest

from scripts.har_parser import parse_har
from scripts.state_manager import (
    advance_wave,
    archive_session,
    init_session,
    resume_session,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestHarToStateFlow:
    """验证 HAR 解析结果能正确保存到 state 并通过 resume/archive 管理。"""

    def test_full_pipeline(self, tmp_path: Path) -> None:
        """HAR 解析 → init_session → advance_wave*4 → archive 完整流程。"""
        har_path = FIXTURES_DIR / "sample.har"
        profiles_path = FIXTURES_DIR / "sample_repo_profiles.yaml"

        # 1. 解析 HAR
        result = parse_har(har_path, profiles_path)
        assert len(result.endpoints) > 0

        # 2. 初始化 state
        state = init_session(tmp_path, str(har_path))
        assert state.current_wave == 0

        # 3. 推进 4 个波次
        for wave_num in range(1, 5):
            state = advance_wave(tmp_path, wave_num, data={
                "endpoint_count": len(result.endpoints) if wave_num == 1 else None,
            })
            assert state.current_wave == wave_num

        # 4. resume 验证
        resumed = resume_session(tmp_path)
        assert resumed is not None
        assert resumed.current_wave == 4

        # 5. archive
        history_dir = archive_session(tmp_path)
        assert history_dir is not None
        assert history_dir.exists()
        assert (history_dir / "state.json").exists()
        # 原文件应已移动
        assert not (tmp_path / ".tide" / "state.json").exists()

    def test_resume_no_session(self, tmp_path: Path) -> None:
        """无 session 时 resume 返回 None。"""
        assert resume_session(tmp_path) is None

    def test_archive_no_session(self, tmp_path: Path) -> None:
        """无 session 时 archive 返回 None。"""
        assert archive_session(tmp_path) is None
