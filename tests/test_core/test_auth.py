from __future__ import annotations

import pytest

from manus_cli.core.auth import resolve_api_key
from manus_cli.core.config import ManusConfig, save_config
from manus_cli.core.errors import AuthenticationError


class TestResolveFromEnv:
    def test_resolve_from_env(self, monkeypatch):
        """resolve_api_key should return the MANUS_API_KEY env var when set."""
        monkeypatch.setenv("MANUS_API_KEY", "sk-env-key-456")

        key = resolve_api_key()

        assert key == "sk-env-key-456"


class TestResolveFromConfig:
    def test_resolve_from_config(self, tmp_config, monkeypatch):
        """resolve_api_key should fall back to the config file api_key."""
        monkeypatch.delenv("MANUS_API_KEY", raising=False)

        save_config(ManusConfig(api_key="sk-config-key-789"))

        key = resolve_api_key()

        assert key == "sk-config-key-789"


class TestResolveRaisesWhenMissing:
    def test_resolve_raises_when_missing(self, tmp_config, monkeypatch):
        """resolve_api_key should raise AuthenticationError when no key found."""
        monkeypatch.delenv("MANUS_API_KEY", raising=False)

        with pytest.raises(AuthenticationError, match="No API key found"):
            resolve_api_key()
