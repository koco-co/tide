"""Tests for hook system."""
from scripts.hooks import HookPoint, HookRegistration, HookRegistry


class TestHookRegistry:
    """Hook registry tests."""

    def test_register_and_get(self) -> None:
        registry = HookRegistry()
        hook = HookRegistration(
            point=HookPoint.WAVE1_PARSE_AFTER,
            name="test-hook",
            command="echo test",
        )
        registry.register(hook)
        hooks = registry.get_hooks(HookPoint.WAVE1_PARSE_AFTER)
        assert len(hooks) == 1
        assert hooks[0].name == "test-hook"

    def test_empty_registry(self) -> None:
        registry = HookRegistry()
        assert not registry.has_hooks(HookPoint.WAVE1_PARSE_BEFORE)
        assert registry.get_hooks(HookPoint.WAVE1_PARSE_BEFORE) == []

    def test_multiple_hooks_same_point(self) -> None:
        registry = HookRegistry()
        for i in range(3):
            registry.register(HookRegistration(
                point=HookPoint.OUTPUT_NOTIFY,
                name=f"hook-{i}",
                command=f"cmd-{i}",
            ))
        assert len(registry.get_hooks(HookPoint.OUTPUT_NOTIFY)) == 3
