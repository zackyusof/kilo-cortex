# Kilo Cortex — Dockerized Memory System

**Plug-and-play memory backend.** Clone, run, and you have a fully functional memory system with vector search, caching, and knowledge base.

```bash
git clone https://git.zyusof.net/zack/kilo-cortex.git
cd kilo-cortex
cp .env.example .env          # Optional: customize defaults
docker compose up -d
```

## Quick Start

```bash
# Start all services (CPU mode, no Obsidian)
docker compose up -d

# Start with Obsidian vault
docker compose --profile obsidian up -d

# Start with GPU support (uncomment GPU config in compose file first)
# docker compose --profile gpu up -d

# Start everything
docker compose up -d

# View status
docker compose ps

# Check health
curl http://localhost:8088/health | python3 -m json.tool
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| **MariaDB** | `3306` | Primary memory store (14 tables) |
| **Redis** | `6379` | L1 hot cache with persistence |
| **Qdrant** | `6333` / `6334` | Vector search (REST / gRPC) |
| **Ollama** | `11434` | Embedding service (CPU: all-minilm) |
| **Memory API** | `8088` | FastAPI HTTP interface |
| **Obsidian** | `3000` / `5900` | Web UI / VNC (optional) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check + service status |
| `GET` | `/health` | Same as root |
| `POST` | `/memories` | Create a memory entry |
| `GET` | `/memories` | List memories (with filters) |
| `GET` | `/memories/{id}` | Get single memory |
| `DELETE` | `/memories/{id}` | Delete a memory |
| `POST` | `/search` | Semantic + keyword hybrid search |
| `GET` | `/sessions/{id}` | Get session with memories |
| `POST` | `/sessions` | Create a new session |
| `GET` | `/rules` | List learned rules |
| `POST` | `/rules` | Create a learned rule |
| `PUT` | `/config/{field}` | Update configuration |
| `GET` | `/config/{field}` | Get config history |
| `GET` | `/quality` | List quality reports |
| `POST` | `/quality/check` | Run quality checks |
| `GET` | `/stats` | System statistics |
| `POST` | `/ingest` | Queue memory for ingestion |
| `POST` | `/ingest/process` | Process queued memories |
| `GET` | `/telemetry` | Query telemetry report |
| `GET` | `/models` | List Ollama models |
| `POST` | `/models/pull` | Pull an embedding model |
| `GET` | `/collections` | List Qdrant collections |
| `GET` | `/export` | Export all data as JSON |

### Example: Create a Memory

```bash
curl -s http://localhost:8088/memories \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"content": "The user prefers Python over Go for backend work", "category": "preference"}'
```

### Example: Search

```bash
curl -s http://localhost:8088/search \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "programming preferences"}'
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Memory API  │────▶│   MariaDB   │     │    Redis    │
│  (FastAPI)   │     │  (14 tables)│     │  (L1 cache) │
│  :8088       │     └─────────────┘     └─────────────┘
└──────┬───────┐
       │       │
       ▼       ▼
┌─────────────┐     ┌─────────────┐
│   Qdrant    │     │   Ollama    │
│  (vector)   │◀────│ (embedding) │
│  :6333      │     │  :11434     │
└─────────────┘     └─────────────┘
       ▲
       │ (optional)
┌──────┴───────┐
│  Obsidian    │
│   (L4 vault) │
│  :3000/:5900 │
└──────────────┘
```

**Memory Layers:**
- **L1** — Redis hot cache (sub-millisecond lookups)
- **L2** — MariaDB primary store + Qdrant vector search
- **L3** — Ollama embeddings for semantic similarity
- **L4** — Obsidian vault for rich knowledge base

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `MARIADB_ROOT_PASSWORD` | `kilo_root_change_me` | MariaDB root password |
| `MARIADB_USER` | `kilo` | Database user |
| `MARIADB_PASSWORD` | `kilo_pass_change_me` | Database password |
| `REDIS_PASSWORD` | `kilo_redis_change_me` | Redis authentication |
| `QDRANT_API_KEY` | `kilo_qdrant_change_me` | Qdrant API key |
| `OLLAMA_GPU` | `false` | Enable GPU passthrough |
| `EMBEDDING_MODEL` | `all-minilm` | Default embedding model |

## Volume Layout

```
data/
├── mariadb/data     # MariaDB persistent storage
├── mariadb/init/    # SQL init scripts (read-only)
├── redis/data       # Redis persistence
├── redis/redis.conf # Redis configuration
├── qdrant/          # Qdrant vector storage
├── ollama/          # Ollama model storage
└── obsidian/        # Obsidian vault + config (optional)
```

## GPU Support

1. Uncomment the `deploy:` section under `ollama-gpu` in `docker-compose.yaml`
2. Ensure NVIDIA Container Toolkit is installed
3. Run with: `OLLAMA_GPU=true docker compose up -d`

## Troubleshooting

```bash
# Check service health
curl http://localhost:8088/health | python3 -m json.tool

# View logs
docker compose logs -f memory-api
docker compose logs -f mariadb
docker compose logs -f qdrant

# Re-run bootstrap (if needed)
docker compose down
docker compose up -d
docker compose up kilo-init

# Reset everything
docker compose down -v    # WARNING: deletes all data
docker compose up -d
```

## License

MIT
