from __future__ import annotations

from typer.testing import CliRunner

import manus_cli.api.client as client_mod
from manus_cli.cli import app
from manus_cli.core.errors import AuthenticationError


runner = CliRunner()


def _raise_authentication_error() -> str:
    raise AuthenticationError(
        "No API key found. Set MANUS_API_KEY env var or run `manus auth login`."
    )


class TestCliErrorHandling:
    def test_task_list_renders_auth_error_without_traceback(self, monkeypatch):
        """task list should render a friendly auth error instead of a traceback."""
        monkeypatch.setattr(client_mod, "resolve_api_key", _raise_authentication_error)

        result = runner.invoke(app, ["task", "list"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "No API key found" in result.output
        assert "Traceback" not in result.output

    def test_chat_renders_auth_error_without_traceback(self, monkeypatch):
        """chat should render a friendly auth error instead of a traceback."""
        monkeypatch.setattr(client_mod, "resolve_api_key", _raise_authentication_error)

        result = runner.invoke(app, ["chat"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "No API key found" in result.output
        assert "Traceback" not in result.output
