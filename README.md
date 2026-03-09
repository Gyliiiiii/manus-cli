# Manus CLI

CLI tool for [Manus AI Agent API](https://manus.ai) — interactive REPL & one-shot task execution.

## Install

```bash
# Requires Python >= 3.11
pip install -e .
```

## Quick Start

```bash
# Login
manus auth login

# One-shot
manus run "What is the capital of France?"
manus -p "Summarize this article"

# Interactive REPL (multi-turn conversation)
manus
```

## Commands

| Command | Description |
|---|---|
| `manus` | Start interactive REPL |
| `manus run "prompt"` | One-shot task |
| `manus -p "prompt"` | One-shot task (option form) |
| `manus chat` | Start REPL (explicit) |
| `manus auth login` | Authenticate with API key |
| `manus auth logout` | Remove saved API key |
| `manus auth status` | Show auth status |
| `manus task list` | List recent tasks |
| `manus task get <id>` | Show task details |
| `manus task delete <id>` | Delete a task |
| `manus file upload <path>` | Upload a file |
| `manus file list` | List uploaded files |
| `manus config set <key> <val>` | Set config value |
| `manus config show` | Show all config |

## REPL Slash Commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/model <name>` | Switch model (manus-1.6, lite, max) |
| `/attach <path>` | Attach file to next prompt |
| `/files` | List uploaded files |
| `/status` | Show current task status |
| `/clear` | Start new conversation |
| `/history` | Show conversation history |
| `/exit` | Exit REPL |

## Configuration

API key resolution order:
1. `MANUS_API_KEY` environment variable
2. `~/.manus/config.toml`

```bash
# Or set directly
export MANUS_API_KEY=your-key-here
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
