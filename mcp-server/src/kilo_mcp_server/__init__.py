"""Kilo Cortex MCP Server - Model Context Protocol for the Kilo Memory System."""

from .server import server


def run():
    """Entry point for console script."""
    from .__main__ import run as _run

    _run()


if __name__ == "__main__":
    run()
