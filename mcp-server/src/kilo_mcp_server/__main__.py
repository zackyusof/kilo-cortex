"""Entry point for the Kilo Cortex MCP server."""

import sys
import asyncio
import anyio

from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.server import stdio
from mcp.server.stdio import stdio_server
from .server import server


async def main():
    """Start the MCP server with stdio transport."""
    import logging
    from structlog.stdlib import get_logger

    logging.basicConfig(level=logging.WARNING)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run():
    """Sync entry point for console script."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
