from __future__ import annotations

import os

from manus_cli.core.config import load_config
from manus_cli.core.errors import AuthenticationError


def resolve_api_key() -> str:
    key = os.environ.get("MANUS_API_KEY")
    if key:
        return key

    config = load_config()
    if config.api_key:
        return config.api_key

    raise AuthenticationError(
        "No API key found. Set MANUS_API_KEY env var or run `manus auth login`."
    )
