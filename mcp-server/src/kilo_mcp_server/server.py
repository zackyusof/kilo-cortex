"""MCP server wrapping Kilo Cortex memory system."""

import json
from typing import Any

from mcp import Tool
from mcp.server import Server
from structlog import get_logger

from .client import CortexClient
from .config import settings
from .models import (
    ExportFormat,
    ExportRequest,
    FulltextSearchRequest,
    HybridSearchRequest,
    MemoryCreate,
    MemoryType,
    MemoryUpdate,
    RulesRequest,
    RuleCreate,
    SemanticSearchRequest,
    SessionCreate,
    VectorSearchRequest,
)

logger = get_logger("kilo_mcp_server")

# --- MCP Server Instance ---

server = Server("kilo-cortex-mcp")
client = CortexClient()

# =====================================================================
# TOOLS
# =====================================================================


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # Memory CRUD
        Tool(
            name="memory_create",
            description="Create a new memory entry in the Kilo Cortex system. Memories are typed (episodic, semantic, procedural, emotional, perceptual) and searchable via multiple backends.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The memory content/text",
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": [
                            "episodic",
                            "semantic",
                            "procedural",
                            "emotional",
                            "perceptual",
                        ],
                        "description": "Type of memory",
                    },
                    "sector": {
                        "type": "string",
                        "description": "Optional sector filter",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional key-value metadata",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="memory_get",
            description="Retrieve a memory by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Memory ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="memory_update",
            description="Update an existing memory by ID. Only provided fields are updated.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Memory ID"},
                    "content": {"type": "string", "description": "Updated content"},
                    "memory_type": {
                        "type": "string",
                        "enum": [
                            "episodic",
                            "semantic",
                            "procedural",
                            "emotional",
                            "perceptual",
                        ],
                        "description": "Updated type",
                    },
                    "sector": {"type": "string", "description": "Updated sector"},
                    "metadata": {"type": "object", "description": "Updated metadata"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="memory_delete",
            description="Delete a memory by its ID. This is irreversible.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Memory ID to delete"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="memory_list",
            description="List memories with pagination. Optionally filter by sector.",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {
                        "type": "integer",
                        "default": 1,
                        "description": "Page number",
                    },
                    "page_size": {
                        "type": "integer",
                        "default": 20,
                        "description": "Results per page",
                    },
                    "sector": {
                        "type": "string",
                        "description": "Optional sector filter",
                    },
                },
            },
        ),
        # Search
        Tool(
            name="search_vector",
            description="Vector similarity search using Qdrant embeddings. Finds memories semantically similar to the query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of results",
                    },
                    "sector": {
                        "type": "string",
                        "description": "Optional sector filter",
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Minimum similarity score (0-1)",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_fulltext",
            description="Full-text search over memory content using MariaDB FTS5. Best for exact keyword matching.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "page": {
                        "type": "integer",
                        "default": 1,
                        "description": "Page number",
                    },
                    "page_size": {
                        "type": "integer",
                        "default": 20,
                        "description": "Results per page",
                    },
                    "sector": {
                        "type": "string",
                        "description": "Optional sector filter",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_hybrid",
            description="Combined vector + full-text search. Balances semantic understanding with keyword precision.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of results",
                    },
                    "vector_weight": {
                        "type": "number",
                        "default": 0.5,
                        "description": "Weight for vector component (0-1)",
                    },
                    "text_weight": {
                        "type": "number",
                        "default": 0.5,
                        "description": "Weight for text component (0-1)",
                    },
                    "sector": {
                        "type": "string",
                        "description": "Optional sector filter",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_semantic",
            description="Semantic cluster search. Groups similar memories into clusters then returns top matches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "cluster_size": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of clusters to form",
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 20,
                        "description": "Total results to return",
                    },
                },
                "required": ["query"],
            },
        ),
        # Sessions
        Tool(
            name="session_create",
            description="Create a new conversation session for organizing memories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Optional session name"},
                    "metadata": {
                        "type": "object",
                        "description": "Optional session metadata",
                    },
                },
            },
        ),
        Tool(
            name="session_get",
            description="Retrieve session details by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Session ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="session_list",
            description="List all conversation sessions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {
                        "type": "integer",
                        "default": 1,
                        "description": "Page number",
                    },
                    "page_size": {
                        "type": "integer",
                        "default": 20,
                        "description": "Results per page",
                    },
                },
            },
        ),
        Tool(
            name="session_delete",
            description="Delete a session and its associated memories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Session ID to delete"},
                },
                "required": ["id"],
            },
        ),
        # Rules
        Tool(
            name="rules_list",
            description="List learned rules with optional category filtering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Max results",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter",
                    },
                },
            },
        ),
        Tool(
            name="rules_learned",
            description="Fetch top learned rules ranked by confidence/priority.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Max results",
                    },
                },
            },
        ),
        Tool(
            name="rule_add",
            description="Add a new learned rule to the system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "rule": {"type": "string", "description": "The rule text"},
                    "category": {"type": "string", "description": "Optional category"},
                    "confidence": {
                        "type": "number",
                        "description": "Optional confidence score (0-1)",
                    },
                },
                "required": ["rule"],
            },
        ),
        # Patterns
        Tool(
            name="patterns_list",
            description="List all pattern triggers and their response templates.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # Ingest / Export
        Tool(
            name="ingest",
            description="Bulk ingest memories from an external data source.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Data source identifier",
                    },
                    "data": {
                        "type": "array",
                        "description": "Array of memory objects to ingest",
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": [
                            "episodic",
                            "semantic",
                            "procedural",
                            "emotional",
                            "perceptual",
                        ],
                        "description": "Optional memory type for all ingested items",
                    },
                },
                "required": ["source", "data"],
            },
        ),
        Tool(
            name="export",
            description="Export memories in the specified format (json, csv, markdown).",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["json", "csv", "markdown"],
                        "default": "json",
                        "description": "Export format",
                    },
                    "filter_sector": {
                        "type": "string",
                        "description": "Optional sector filter",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional result limit",
                    },
                },
            },
        ),
    ]


# --- Tool Handlers ---


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list:
    try:
        handler = _TOOL_HANDLERS.get(name)
        if not handler:
            return [{"type": "text", "text": f"Unknown tool: {name}"}]

        result = handler(arguments)
        return [{"type": "text", "text": json.dumps(result, default=str, indent=2)}]

    except Exception as e:
        logger.error("tool_error", tool=name, error=str(e))
        return [{"type": "text", "text": f"Error: {e}"}]


# =====================================================================
# RESOURCE HANDLERS
# =====================================================================


@server.list_resources()
async def list_resources() -> list:
    return [
        {
            "uri": "memory://list",
            "name": "Memory List",
            "description": "Current memory overview with counts by type",
            "mimeType": "application/json",
        },
        {
            "uri": "rules://learned",
            "name": "Learned Rules",
            "description": "Top learned rules from the knowledge base",
            "mimeType": "text/plain",
        },
        {
            "uri": "stats://overview",
            "name": "System Stats",
            "description": "Kilo Cortex system statistics and health",
            "mimeType": "application/json",
        },
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    try:
        handler = _RESOURCE_HANDLERS.get(uri)
        if not handler:
            return f"Resource not found: {uri}"
        return handler()

    except Exception as e:
        logger.error("resource_error", uri=str(uri), error=str(e))
        return f"Error reading resource: {e}"


# =====================================================================
# PROMPT HANDLERS
# =====================================================================


@server.list_prompts()
async def list_prompts() -> list:
    return [
        {
            "name": "memory-search",
            "description": "Search through your knowledge base and return relevant memories",
            "arguments": [
                {
                    "name": "query",
                    "description": "What you want to search for",
                    "required": True,
                },
                {
                    "name": "search_type",
                    "description": "Search method: vector, fulltext, hybrid, or semantic",
                    "required": False,
                },
            ],
        },
        {
            "name": "session-context",
            "description": "Load a conversation session to provide context for the current task",
            "arguments": [
                {
                    "name": "session_id",
                    "description": "The session ID to load",
                    "required": True,
                },
            ],
        },
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict | None) -> dict:
    try:
        handler = _PROMPT_HANDLERS.get(name)
        if not handler:
            return {"error": f"Unknown prompt: {name}"}

        args = arguments or {}
        result = handler(args)
        return result

    except Exception as e:
        logger.error("prompt_error", prompt=name, error=str(e))
        return {"error": f"Error: {e}"}


# =====================================================================
# TOOL HANDLER MAP
# =====================================================================

_TOOL_HANDLERS: dict[str, Any] = {
    "memory_create": lambda args: {
        "result": client.memory_create(
            MemoryCreate(**{k: v for k, v in args.items() if v is not None})
        ).model_dump()
    },
    "memory_get": lambda args: {
        "result": client.memory_get(int(args["id"])).model_dump()
    },
    "memory_update": lambda args: {
        "result": client.memory_update(
            int(args["id"]),
            MemoryUpdate(
                **{k: v for k, v in args.items() if k != "id" and v is not None}
            ),
        ).model_dump()
    },
    "memory_delete": lambda args: client.memory_delete(int(args["id"])),
    "memory_list": lambda args: {
        "result": client.memory_list(
            page=int(args.get("page", 1)),
            page_size=int(args.get("page_size", 20)),
            sector=args.get("sector"),
        ).model_dump()
    },
    "search_vector": lambda args: client.search_vector(
        VectorSearchRequest(**{k: v for k, v in args.items() if v is not None})
    ).model_dump(),
    "search_fulltext": lambda args: client.search_fulltext(
        FulltextSearchRequest(**{k: v for k, v in args.items() if v is not None})
    ).model_dump(),
    "search_hybrid": lambda args: client.search_hybrid(
        HybridSearchRequest(**{k: v for k, v in args.items() if v is not None})
    ).model_dump(),
    "search_semantic": lambda args: client.search_semantic(
        SemanticSearchRequest(**{k: v for k, v in args.items() if v is not None})
    ).model_dump(),
    "session_create": lambda args: {
        "result": client.session_create(
            SessionCreate(**{k: v for k, v in args.items() if v is not None})
        ).model_dump()
    }
    if args
    else {"result": client.session_create().model_dump()},
    "session_get": lambda args: client.session_get(args["id"]).model_dump(),
    "session_list": lambda args: {
        "sessions": client.session_list(
            page=int(args.get("page", 1)),
            page_size=int(args.get("page_size", 20)),
        )
    },
    "session_delete": lambda args: client.session_delete(args["id"]),
    "rules_list": lambda args: client.rules_list(
        RulesRequest(**{k: v for k, v in args.items() if v is not None})
        if args
        else None
    ),
    "rules_learned": lambda args: client.rules_learned(
        limit=int(args.get("limit", 50))
    ),
    "rule_add": lambda args: client.rule_add(
        RuleCreate(**{k: v for k, v in args.items() if v is not None})
    ),
    "patterns_list": lambda args: client.patterns_list(),
    "ingest": lambda args: client.ingest(args),
    "export": lambda args: client.export(
        ExportRequest(
            format=ExportFormat(args.get("format", "json")),
            filter_sector=args.get("filter_sector"),
            limit=args.get("limit"),
        )
    ),
}

# =====================================================================
# RESOURCE HANDLER MAP
# =====================================================================

_RESOURCE_HANDLERS: dict[str, Any] = {
    "memory://list": lambda: json.dumps(
        {
            "stats": client.stats(),
            "recent": client.memory_list(page_size=10).model_dump(),
        },
        default=str,
    ),
    "rules://learned": lambda: "\n".join(
        f"- {r.get('rule', 'unknown')}" for r in client.rules_learned(limit=20)
    ),
    "stats://overview": lambda: json.dumps(client.stats(), default=str),
}

# =====================================================================
# PROMPT HANDLER MAP
# =====================================================================

_PROMPT_HANDLERS: dict[str, Any] = {
    "memory-search": lambda args: {
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"Search the knowledge base for: {args.get('query', '')}",
                },
            },
            {
                "role": "assistant",
                "content": {
                    "type": "text",
                    "text": f"[Searching with {args.get('search_type', 'hybrid')}...]",
                },
            },
        ],
    },
    "session-context": lambda args: {
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"Load session context for: {args.get('session_id', '')}",
                },
            },
            {
                "role": "assistant",
                "content": {
                    "type": "text",
                    "text": f"[Loading session {args.get('session_id', '')}...]",
                },
            },
        ],
    },
}
