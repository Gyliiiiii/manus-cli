from __future__ import annotations

import pytest


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Redirect config dir to a temp directory."""
    import manus_cli.core.config as config_mod

    config_dir = tmp_path / ".manus"
    config_file = config_dir / "config.toml"
    monkeypatch.setattr(config_mod, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_mod, "CONFIG_FILE", config_file)
    return config_dir
