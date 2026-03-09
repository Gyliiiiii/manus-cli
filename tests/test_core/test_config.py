from __future__ import annotations

from manus_cli.core.config import ManusConfig, load_config, save_config


class TestLoadConfigDefaults:
    def test_load_config_defaults(self, tmp_config):
        """When no config file exists, load_config returns ManusConfig defaults."""
        config = load_config()

        assert config.api_key is None
        assert config.default_model == "manus-1.6"
        assert config.timeout == 600


class TestSaveAndLoadConfig:
    def test_save_and_load_config(self, tmp_config):
        """Saving a config and loading it back should preserve all values."""
        original = ManusConfig(
            api_key="sk-test-key-123",
            default_model="max",
            timeout=300,
        )
        save_config(original)

        loaded = load_config()

        assert loaded.api_key == "sk-test-key-123"
        assert loaded.default_model == "max"
        assert loaded.timeout == 300


class TestSaveConfigCreatesDir:
    def test_save_config_creates_dir(self, tmp_config):
        """save_config should create the config directory if it doesn't exist."""
        assert not tmp_config.exists()

        save_config(ManusConfig(api_key="key"))

        assert tmp_config.exists()
        assert (tmp_config / "config.toml").exists()
