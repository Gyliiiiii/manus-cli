from __future__ import annotations

from manus_cli.repl.commands import create_default_registry


class TestCreateDefaultRegistryHasCommands:
    def test_create_default_registry_has_commands(self):
        """The default registry should contain the expected slash commands."""
        registry = create_default_registry()
        names = registry.names()

        expected = ["attach", "clear", "exit", "files", "help", "history", "model", "quit", "status"]
        assert names == expected

        # Each command should have a non-empty description
        for name in names:
            cmd = registry.get(name)
            assert cmd is not None
            assert cmd.description


class TestRegistryGetUnknownReturnsNone:
    def test_registry_get_unknown_returns_none(self):
        """Looking up a non-existent command should return None."""
        registry = create_default_registry()

        assert registry.get("nonexistent") is None
        assert registry.get("") is None
