"""Tests for preference learning system."""
from pathlib import Path

from scripts.preferences import (
    AutoflowPreferences,
    load_preferences,
    save_preferences,
    update_preferences,
)


class TestPreferences:
    """Preference system tests."""

    def test_default_preferences(self, tmp_path: Path) -> None:
        prefs = load_preferences(tmp_path)
        assert prefs.assertion_verbosity == "normal"
        assert prefs.preferred_fixture_scope == "function"

    def test_save_and_load(self, tmp_path: Path) -> None:
        prefs = AutoflowPreferences(assertion_verbosity="terse", industry="finance")
        save_preferences(tmp_path, prefs)
        loaded = load_preferences(tmp_path)
        assert loaded.assertion_verbosity == "terse"
        assert loaded.industry == "finance"

    def test_update_partial(self, tmp_path: Path) -> None:
        save_preferences(tmp_path, AutoflowPreferences())
        updated = update_preferences(tmp_path, assertion_verbosity="verbose", skip_user_confirmation=True)
        assert updated.assertion_verbosity == "verbose"
        assert updated.skip_user_confirmation is True
        assert updated.preferred_fixture_scope == "function"  # unchanged
