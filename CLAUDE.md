# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# Install (editable + dev deps)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run CLI
manus --version
manus -p "prompt"          # one-shot
manus run "prompt"         # one-shot (alt)
manus                      # interactive REPL

# Tests
pytest                     # all tests
pytest -v                  # verbose
pytest tests/test_core/test_config.py              # single file
pytest tests/test_api/test_client.py -k "success"  # single test by name
```

## Architecture

Async-first Python CLI targeting the Manus AI Agent REST API (`https://api.manus.ai/v1`).

**Dependency flow:**

```
cli.py (Typer entry) ──→ repl/session.py (REPL orchestrator)
    │                         ├→ repl/commands.py (slash command registry)
    │                         ├→ repl/prompt.py (prompt_toolkit config)
    │                         └→ repl/renderer.py (Rich output)
    │
    ├──→ api/tasks.py ──→ api/client.py ──→ core/auth.py ──→ core/config.py
    ├──→ api/files.py ──→ api/client.py
    ├──→ core/poller.py ──→ api/tasks.py
    └──→ utils/display.py (Rich tables)
```

**Key patterns:**
- All HTTP operations are async (`httpx.AsyncClient`). Typer command handlers bridge sync→async via `asyncio.run()`.
- `api/client.py` (`ManusClient`) is the single HTTP gateway. Services (`TaskService`, `FileService`) compose it. Auth header: `API_KEY: <key>`.
- `cli.py` uses lazy imports inside handlers to keep startup fast and avoid circular deps.
- REPL multi-turn: `ReplSession.current_task_id` is passed as `task_id` in `CreateTaskRequest` to continue conversations.
- Slash commands use a registry pattern with async handlers that receive the `ReplSession` instance. `TYPE_CHECKING` guard avoids circular import with session.
- Polling uses exponential backoff (2s → 1.5x → cap 10s, timeout 600s) with Rich Live spinner.

**Config resolution (priority):** `MANUS_API_KEY` env var → `~/.manus/config.toml` → `AuthenticationError`

## Testing Conventions

- pytest-asyncio with `asyncio_mode = "auto"` — async test functions just work, no decorator needed.
- HTTP mocking via `respx` — mock `httpx.AsyncClient` calls, pass `api_key` directly to `ManusClient()` to skip auth resolution.
- `tmp_config` fixture (conftest.py) redirects `CONFIG_DIR`/`CONFIG_FILE` to tmp_path via monkeypatch.
- Class-based test grouping (e.g., `class TestRequestSuccess`).

## Exception Hierarchy

`ManusError` → `AuthenticationError` | `APIError(status_code, detail)` | `TaskFailedError(task_id)` | `TaskTimeoutError(task_id, elapsed)`
