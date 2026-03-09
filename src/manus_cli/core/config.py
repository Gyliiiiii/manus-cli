from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


CONFIG_DIR = Path.home() / ".manus"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass
class ManusConfig:
    api_key: str | None = None
    default_model: str = "manus-1.6"
    timeout: int = 600


def load_config() -> ManusConfig:
    if not CONFIG_FILE.exists():
        return ManusConfig()

    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    valid_keys = {field.name for field in fields(ManusConfig)}
    filtered = {k: v for k, v in data.items() if k in valid_keys}
    return ManusConfig(**filtered)


def save_config(config: ManusConfig) -> None:
    import tomli_w

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    data: dict[str, object] = {}
    for field in fields(config):
        value = getattr(config, field.name)
        if value is not None:
            data[field.name] = value

    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)
