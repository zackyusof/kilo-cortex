# Kilo Cortex MCP Server

Model Context Protocol (MCP) server that wraps the [Kilo Cortex](https://git.zyusof.net/zack/kilo-cortex) memory system API, making it accessible to any MCP-compatible host (Claude Desktop, Cursor, Windsurf, etc.).

## What It Does

Exposes all 23+ Kilo Cortex endpoints as MCP primitives:

| Primitive | Count | Purpose |
|-----------|-------|---------|
| **Tools** | 19 | Memory CRUD, 4 search types, sessions, rules, patterns, ingest/export |
| **Resources** | 3 | Live memory list, learned rules, system stats |
| **Prompts** | 2 | Pre-built memory search and session context templates |

## Installation

```bash
# Install from source
pip install -e .

# Or install globally
pip install .
```

## Configuration

Set via environment variables (or `.env` file):

```bash
CORTEX_API_URL=http://localhost:8000
CORTEX_TIMEOUT_SECONDS=30
CORTEX_LOG_LEVEL=INFO
```

## Usage

### As a CLI tool

```bash
# Stdio mode (default, for MCP hosts)
kilo-mcp

# Or via Python
python -m kilo_mcp_server
```

### As a library

```python
from kilo_mcp_server.server import server
import asyncio

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

asyncio.run(main())
```

### Docker

```bash
docker build -t kilo-cortex-mcp .
docker run -i --env CORTEX_API_URL=http://cortex:8000 kilo-cortex-mcp
```

## MCP Host Configuration

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "kilo-cortex": {
      "command": "kilo-mcp",
      "env": {
        "CORTEX_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "kilo-cortex": {
      "command": "kilo-mcp",
      "args": [],
      "env": {
        "CORTEX_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Available Tools

### Memory
- `memory_create` - Create a new memory entry
- `memory_get` - Retrieve a memory by ID
- `memory_update` - Update an existing memory
- `memory_delete` - Delete a memory
- `memory_list` - List memories with pagination

### Search
- `search_vector` - Vector similarity search (Qdrant)
- `search_fulltext` - Full-text search (MariaDB FTS5)
- `search_hybrid` - Combined vector + full-text
- `search_semantic` - Semantic cluster search

### Sessions
- `session_create` - Create a new conversation session
- `session_get` - Retrieve session details
- `session_list` - List all sessions
- `session_delete` - Delete a session

### Rules & Patterns
- `rules_list` - List learned rules
- `rules_learned` - Fetch top learned rules
- `rule_add` - Add a new learned rule
- `patterns_list` - List pattern triggers

### Utilities
- `ingest` - Bulk ingest from external source
- `export` - Export memories (json/csv/markdown)

## Available Resources

- `memory://list` - Current memory overview (JSON)
- `rules://learned` - Top learned rules (text)
- `stats://overview` - System statistics (JSON)

## Available Prompts

- `memory-search` - Search the knowledge base with configurable search type
- `session-context` - Load a conversation session for context

## Project Structure

```
kilo-cortex-mcp/
├── pyproject.toml           # Project config & dependencies
├── .env.example             # Configuration template
├── README.md
└── src/
    └── kilo_mcp_server/
        ├── __init__.py      # Package entry
        ├── __main__.py      # CLI entry point (stdio transport)
        ├── config.py        # Settings via env vars
        ├── models.py        # Pydantic data models
        ├── client.py        # Cortex API HTTP client
        └── server.py        # MCP server + tools/resources/prompts
```

## Dependencies

- `mcp>=1.9.0` - MCP protocol library
- `httpx>=0.27.0` - Async HTTP client
- `pydantic>=2.0` - Data validation
- `pydantic-settings>=2.0` - Env var config
- `structlog>=24.0` - Structured logging

## Development

```bash
# Install in editable mode
pip install -e ".[dev]"

# Run tests (when available)
pytest

# Lint
ruff check .

# Type check
mypy src/
```

## License

Proprietary - Kilo Systems
