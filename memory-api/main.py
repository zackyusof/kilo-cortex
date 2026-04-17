"""
Kilo Memory System — HTTP API
FastAPI wrapper around memory.py CLI functions.
"""

import os
import json
import time
import hashlib
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── Database connections ──────────────────────────────────────
import pymysql
import redis

# ─── Configuration ────────────────────────────────────────────
MDB_HOST = os.getenv("MARIADB_HOST", "mariadb")
MDB_PORT = int(os.getenv("MARIADB_PORT", "3306"))
MDB_USER = os.getenv("MARIADB_USER", "kilo")
MDB_PASS = os.getenv("MARIADB_PASSWORD", "kilo_pass_change_me")
MDB_NAME = os.getenv("MARIADB_DATABASE", "kilo")

RDS_HOST = os.getenv("REDIS_HOST", "redis")
RDS_PORT = int(os.getenv("REDIS_PORT", "6379"))
RDS_PASS = os.getenv("REDIS_PASSWORD", "kilo_redis_change_me")

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_KEY = os.getenv("QDRANT_API_KEY", "kilo_qdrant_change_me")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "ollama")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-minilm")
DEFAULT_DIMS = int(os.getenv("DEFAULT_DIMS", "384"))


def get_mdb():
    return pymysql.connect(
        host=MDB_HOST,
        port=MDB_PORT,
        user=MDB_USER,
        password=MDB_PASS,
        database=MDB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4",
    )


def get_redis():
    return redis.Redis(
        host=RDS_HOST,
        port=RDS_PORT,
        password=RDS_PASS,
        decode_responses=True,
        socket_timeout=5,
    )


def qdrant_request(method, path, data=None):
    url = f"http://{QDRANT_HOST}:{QDRANT_PORT}{path}"
    headers = {"Content-Type": "application/json", "accept": "application/json"}
    if QDRANT_KEY:
        headers["x-api-key"] = QDRANT_KEY
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers=headers,
        method=method,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def ollama_embed(text):
    url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/embed"
    data = json.dumps({"model": EMBEDDING_MODEL, "input": text}).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    if "embeddings" in result:
        return result["embeddings"][0]
    elif "embedding" in result:
        return result["embedding"]
    raise ValueError(f"Unexpected response format: {result}")


def make_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


# ─── Pydantic models ──────────────────────────────────────────
class MemoryEntry(BaseModel):
    content: str
    category: Optional[str] = "general"
    tags: Optional[list] = None
    session_id: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 20
    session_id: Optional[str] = None


class ConfigChange(BaseModel):
    field: str
    old_value: str
    new_value: str
    session_id: Optional[str] = None


class LogRequest(BaseModel):
    action_type: str
    content: str
    tags: Optional[list] = None
    session_id: Optional[str] = None


class QualityCheck(BaseModel):
    check_type: str
    description: Optional[str] = None


class DiscoveryEntry(BaseModel):
    title: str
    summary: Optional[str] = None
    tags: Optional[list] = None
    entry_id: Optional[int] = None
    session_id: Optional[str] = None


class IngestEntry(BaseModel):
    source: str
    content: str
    event_type: Optional[str] = "batch"
    priority: Optional[int] = 0


# ─── Health check helper ──────────────────────────────────────
def check_service(name, check_fn):
    try:
        ok = check_fn()
        return {"name": name, "status": "healthy" if ok else "unhealthy"}
    except Exception as e:
        return {"name": name, "status": "unhealthy", "error": str(e)}


def check_mariadb():
    conn = pymysql.connect(
        host=MDB_HOST,
        port=MDB_PORT,
        user=MDB_USER,
        password=MDB_PASS,
        database=MDB_NAME,
        connect_timeout=5,
    )
    conn.close()
    return True


def check_redis():
    r = get_redis()
    r.ping()
    return True


def check_qdrant():
    result = qdrant_request("GET", "/health")
    return result is not None


def check_ollama():
    try:
        resp = urllib.request.urlopen(
            f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags", timeout=5
        )
        return resp.status == 200
    except:
        return False


# ─── App lifespan ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"  Kilo Memory API starting — model={EMBEDDING_MODEL}, dims={DEFAULT_DIMS}")
    yield


app = FastAPI(
    title="Kilo Memory System",
    description="HTTP API for the Kilo Memory System — MariaDB + Redis + Qdrant vector search",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Health endpoint ──────────────────────────────────────────
@app.get("/health")
@app.get("/")
async def health():
    return {
        "status": "ok",
        "service": "kilo-memory-api",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": [
            check_service("mariadb", check_mariadb),
            check_service("redis", check_redis),
            check_service("qdrant", check_qdrant),
            check_service("ollama", check_ollama),
        ],
    }


# ─── Memory CRUD ──────────────────────────────────────────────
@app.post("/memories", response_model=dict)
async def create_memory(entry: MemoryEntry):
    """Create a new memory entry with optional embedding."""
    conn = get_mdb()
    r = get_redis()
    try:
        cur = conn.cursor()

        # Dedup check
        h = make_hash(entry.content[:500])
        cur.execute(
            "SELECT id FROM memory_entries WHERE SHA2(%s, 256) = %s AND created_at > NOW() - INTERVAL 30 SECOND",
            (entry.content, h),
        )
        if cur.fetchone():
            return {
                "id": None,
                "status": "duplicate",
                "message": "Similar entry exists within 30s window",
            }

        # Get or create session
        session_id = entry.session_id
        if not session_id:
            cur.execute(
                "SELECT id FROM sessions WHERE session_id = %s ORDER BY start_time DESC LIMIT 1",
                (session_id or "default"),
            )
            sess = cur.fetchone()
            if not sess:
                cur.execute(
                    "INSERT INTO sessions (session_id, start_time) VALUES (%s, NOW())",
                    ("default" if not session_id else session_id),
                )
                session_id = cur.lastrow_id

        # Insert memory
        tags_json = json.dumps(entry.tags) if entry.tags else None
        cur.execute(
            """INSERT INTO memory_entries (content, category, tags, quality_score, strength, created_at)
               VALUES (%s, %s, %s, 1.00, 100.00, NOW())""",
            (entry.content, entry.category or "general", tags_json),
        )
        entry_id = cur.lastrow_id

        # Generate embedding if model is available
        embedding_id = None
        try:
            vec = ollama_embed(entry.content)
            dims = len(vec)

            # Determine collection
            collection = (
                "kilo-learned-rules"
                if entry.category == "rule"
                else "kilo-session-history"
            )

            # Upsert in Qdrant
            qdrant_request(
                "PUT",
                f"/collections/{collection}/points/unused",
                {
                    "points": [
                        {
                            "id": entry_id,
                            "vector": vec,
                            "payload": {
                                "content": entry.content,
                                "category": entry.category or "general",
                                "entry_id": entry_id,
                                "created_at": datetime.now(timezone.utc).isoformat(),
                            },
                        }
                    ]
                },
            )
            embedding_id = f"qdrant:{collection}:{entry_id}"
            cur.execute(
                "UPDATE memory_entries SET embedding_id = %s WHERE id = %s",
                (embedding_id, entry_id),
            )
        except Exception as e:
            # Embedding failure is non-fatal
            print(f"  ⚠️  Embedding failed: {e}")

        # Invalidate caches
        r.delete("kilo:stats:*")
        r.delete("kilo:search:*")

        conn.commit()
        return {"id": entry_id, "status": "created", "embedding": embedding_id}
    finally:
        conn.close()


@app.get("/memories/{entry_id}", response_model=dict)
async def get_memory(entry_id: int):
    """Get a single memory entry by ID."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM memory_entries WHERE id = %s", (entry_id,))
        entry = cur.fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        return entry
    finally:
        conn.close()


@app.get("/memories", response_model=list)
async def list_memories(
    category: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session_id: Optional[str] = None,
):
    """List memory entries with optional filters."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM memory_entries WHERE 1=1"
        params = []

        if category:
            query += " AND category = %s"
            params.append(category)
        if session_id:
            query += " AND id IN (SELECT memory_id FROM hebbian_links WHERE source_id IN (SELECT id FROM sessions WHERE session_id = %s))"
            params.append(session_id)
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, params)
        return cur.fetchall()
    finally:
        conn.close()


@app.delete("/memories/{entry_id}", response_model=dict)
async def delete_memory(entry_id: int):
    """Delete a memory entry."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM memory_entries WHERE id = %s", (entry_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        conn.commit()
        return {"status": "deleted", "id": entry_id}
    finally:
        conn.close()


# ─── Search ───────────────────────────────────────────────────
@app.post("/search", response_model=dict)
async def search_memories(req: SearchRequest):
    """Semantic search across memory entries using vector + keyword hybrid."""
    conn = get_mdb()
    r = get_redis()
    try:
        # Check cache
        cache_key = f"kilo:search:{make_hash(req.query)[:16]}"
        cached = r.get(cache_key)
        if cached and req.query != "":
            results = json.loads(cached)
            return {"results": results, "cached": True, "query": req.query}

        results = []

        # Vector search in Qdrant
        if req.query:
            try:
                vec = ollama_embed(req.query)
                for collection in ["kilo-session-history", "kilo-learned-rules"]:
                    points = qdrant_request(
                        "GET",
                        f"/collections/{collection}/points/search",
                        {"vector": vec, "limit": req.limit, "with_payload": True},
                    )
                    for point in points.get("result", []):
                        payload = point.get("payload", {})
                        results.append(
                            {
                                "type": "vector",
                                "score": point.get("score", 0),
                                "entry_id": payload.get("entry_id"),
                                "content": payload.get("content", ""),
                                "category": payload.get("category", "general"),
                            }
                        )
            except Exception as e:
                print(f"  ⚠️  Vector search failed: {e}")

        # Fallback: keyword search in MariaDB
        if not results or req.query:
            cur = conn.cursor()
            search_term = f"%{req.query}%"
            cur.execute(
                """SELECT id, content, category, tags, quality_score, strength,
                          created_at, updated_at
                   FROM memory_entries
                   WHERE content LIKE %s OR category LIKE %s
                   ORDER BY quality_score DESC, strength DESC
                   LIMIT %s""",
                (search_term, search_term, req.limit),
            )
            for row in cur.fetchall():
                results.append(
                    {
                        "type": "keyword",
                        "score": 1.0,
                        "entry_id": row["id"],
                        "content": row["content"],
                        "category": row["category"],
                        "quality_score": row["quality_score"],
                        "strength": row["strength"],
                        "created_at": str(row["created_at"]),
                    }
                )

        # Sort by score and deduplicate
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        seen = set()
        unique = []
        for r in results:
            eid = r.get("entry_id")
            if eid and eid not in seen:
                seen.add(eid)
                unique.append(r)

        # Cache results
        if req.query:
            r.setex(cache_key, 300, json.dumps(unique))

        return {"results": unique[: req.limit], "cached": False, "query": req.query}
    finally:
        conn.close()


# ─── Sessions ─────────────────────────────────────────────────
@app.get("/sessions/{session_id}", response_model=dict)
async def get_session(session_id: str):
    """Get session info and all associated memories."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM sessions WHERE session_id = %s ORDER BY start_time DESC LIMIT 1",
            (session_id,),
        )
        session = cur.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get memories for this session
        cur.execute(
            """SELECT me.* FROM memory_entries me
               JOIN hebbian_links hl ON me.id = hl.target_id
               WHERE hl.source_id = %s
               ORDER BY me.created_at""",
            (session["id"],),
        )
        memories = cur.fetchall()

        return {"session": session, "memory_count": len(memories), "memories": memories}
    finally:
        conn.close()


@app.post("/sessions", response_model=dict)
async def create_session(session_id: Optional[str] = None):
    """Create a new session."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        sid = session_id or f"session-{int(time.time())}"
        cur.execute(
            "INSERT INTO sessions (session_id, start_time) VALUES (%s, NOW())", (sid,)
        )
        conn.commit()
        return {"session_id": sid, "status": "created"}
    finally:
        conn.close()


# ─── Learned Rules ────────────────────────────────────────────
@app.get("/rules", response_model=list)
async def list_rules(rule_type: Optional[str] = None, limit: int = 50):
    """List learned rules."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM learned_rules WHERE 1=1"
        params = []
        if rule_type:
            query += " AND rule_type = %s"
            params.append(rule_type)
        query += " ORDER BY confidence DESC LIMIT %s"
        params.append(limit)
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        conn.close()


@app.post("/rules", response_model=dict)
async def create_rule(rule: dict):
    """Create a learned rule."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO learned_rules (rule_type, pattern, action, confidence, created_at)
               VALUES (%s, %s, %s, %s, NOW())""",
            (
                rule.get("rule_type", "general"),
                rule.get("pattern", ""),
                rule.get("action", ""),
                rule.get("confidence", 0.5),
            ),
        )
        conn.commit()
        return {"id": cur.lastrow_id, "status": "created"}
    finally:
        conn.close()


# ─── Config ───────────────────────────────────────────────────
@app.put("/config/{field}", response_model=dict)
async def update_config(field: str, body: ConfigChange):
    """Update a configuration value."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO config_changes (config_key, old_value, new_value, created_at)
               VALUES (%s, %s, %s, NOW())""",
            (field, body.old_value, body.new_value),
        )
        conn.commit()
        return {"status": "updated", "field": field}
    finally:
        conn.close()


@app.get("/config/{field}", response_model=dict)
async def get_config(field: str):
    """Get config change history for a field."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM config_changes WHERE config_key = %s ORDER BY created_at DESC",
            (field,),
        )
        return cur.fetchall()
    finally:
        conn.close()


# ─── Quality ──────────────────────────────────────────────────
@app.get("/quality", response_model=list)
async def list_quality_reports(limit: int = 10):
    """List quality reports."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM memory_quality_report ORDER BY assessed_at DESC LIMIT %s",
            (limit,),
        )
        return cur.fetchall()
    finally:
        conn.close()


@app.post("/quality/check", response_model=dict)
async def check_quality(req: QualityCheck):
    """Run a quality check."""
    conn = get_mdb()
    try:
        cur = conn.cursor()

        if req.check_type == "entries":
            cur.execute(
                """SELECT me.id, me.content, me.quality_score,
                          COUNT(f.id) as feedback_count
                   FROM memory_entries me
                   LEFT JOIN feedback_log f ON me.id = f.memory_id
                   WHERE me.quality_score < 0.50
                   ORDER BY me.quality_score ASC
                   LIMIT 20"""
            )
            return {"type": "low_quality", "entries": cur.fetchall()}
        elif req.check_type == "stale":
            cur.execute(
                """SELECT id, content, last_retrieved, strength
                   FROM memory_entries
                   WHERE last_retrieved < NOW() - INTERVAL 30 DAY
                   ORDER BY strength ASC
                   LIMIT 20"""
            )
            return {"type": "stale", "entries": cur.fetchall()}
        elif req.check_type == "orphaned":
            cur.execute(
                """SELECT me.id, me.content, me.created_at
                   FROM memory_entries me
                   LEFT JOIN hebbian_links hl ON me.id = hl.source_id OR me.id = hl.target_id
                   WHERE hl.id IS NULL
                   ORDER BY me.created_at ASC
                   LIMIT 20"""
            )
            return {"type": "orphaned", "entries": cur.fetchall()}
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown check type: {req.check_type}"
            )
    finally:
        conn.close()


# ─── Discovery ────────────────────────────────────────────────
@app.post("/discovery", response_model=dict)
async def add_discovery(entry: DiscoveryEntry):
    """Add a discovery entry."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        tags_json = json.dumps(entry.tags) if entry.tags else None
        cur.execute(
            """INSERT INTO discovery_cache (query_hash, query_text, result_json, expires_at)
               VALUES (%s, %s, %s, DATE_ADD(NOW(), INTERVAL 24 HOUR))""",
            (
                make_hash(entry.title),
                entry.title,
                json.dumps({"summary": entry.summary, "tags": entry.tags}),
            ),
        )
        conn.commit()
        return {"id": cur.lastrow_id, "status": "discovered"}
    finally:
        conn.close()


@app.get("/discovery", response_model=list)
async def search_discovery(query: str):
    """Search discovery cache."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, query_text, result_json, hits, created_at
               FROM discovery_cache
               WHERE query_text LIKE %s
               ORDER BY hits DESC, created_at DESC
               LIMIT 20""",
            (f"%{query}%",),
        )
        return cur.fetchall()
    finally:
        conn.close()


# ─── Ingestion ────────────────────────────────────────────────
@app.post("/ingest", response_model=dict)
async def ingest_memory(entry: IngestEntry):
    """Queue a memory for ingestion."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO memory_ingest_log (source, content_hash, content_preview, status, created_at)
               VALUES (%s, %s, %s, 'queued', NOW())""",
            (entry.source, make_hash(entry.content), entry.content[:200]),
        )
        conn.commit()
        return {"id": cur.lastrow_id, "status": "queued", "source": entry.source}
    finally:
        conn.close()


@app.post("/ingest/process", response_model=dict)
async def process_ingest(source_filter: Optional[str] = None):
    """Process queued ingested memories."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        query = """SELECT id, content_hash, content_preview FROM memory_ingest_log
                   WHERE status = 'queued'"""
        params = []
        if source_filter:
            query += " AND source = %s"
            params.append(source_filter)
        query += " LIMIT 10"

        cur.execute(query, params)
        items = cur.fetchall()

        processed = 0
        for item in items:
            cur.execute(
                """INSERT IGNORE INTO memory_entries (content, category, quality_score, strength, created_at)
                   VALUES (%s, 'ingested', 0.80, 50.00, NOW())""",
                (item["content_preview"],),
            )
            cur.execute(
                "UPDATE memory_ingest_log SET status = 'processed', processed_at = NOW() WHERE id = %s",
                (item["id"],),
            )
            processed += 1

        conn.commit()
        return {"processed": processed, "source_filter": source_filter}
    finally:
        conn.close()


@app.get("/ingest/status", response_model=dict)
async def ingest_queue_status():
    """Get ingestion queue status."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, COUNT(*) as count FROM memory_ingest_log GROUP BY status"
        )
        return {"queue": dict((r["status"], r["count"]) for r in cur.fetchall())}
    finally:
        conn.close()


# ─── Stats ────────────────────────────────────────────────────
@app.get("/stats", response_model=dict)
async def get_stats():
    """Get system statistics."""
    conn = get_mdb()
    r = get_redis()
    try:
        cur = conn.cursor()

        # Check cache first
        cached = r.get("kilo:stats:all")
        if cached:
            stats = json.loads(cached)
            stats["cached"] = True
            return stats

        cur.execute("SELECT COUNT(*) as total FROM memory_entries")
        total_memories = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as total FROM learned_rules")
        total_rules = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as total FROM sessions")
        total_sessions = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as total FROM hebbian_links")
        total_links = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as total FROM feedback_log")
        total_feedback = cur.fetchone()["total"]

        cur.execute("SELECT AVG(strength) as avg_strength FROM memory_entries")
        avg_strength = cur.fetchone()["avg_strength"] or 0

        stats = {
            "memories": total_memories,
            "rules": total_rules,
            "sessions": total_sessions,
            "hebbian_links": total_links,
            "feedback": total_feedback,
            "avg_strength": float(avg_strength),
            "cached": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Cache for 60 seconds
        r.setex("kilo:stats:all", 60, json.dumps(stats))
        return stats
    finally:
        conn.close()


# ─── Telemetry ────────────────────────────────────────────────
@app.post("/telemetry", response_model=dict)
async def log_telemetry(
    query_text: str,
    query_type: str = "search",
    result_count: int = 0,
    latency_ms: float = 0,
):
    """Log a telemetry event."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO query_telemetry (query_text, query_type, results_count, response_time_ms, created_at)
               VALUES (%s, %s, %s, %s, NOW())""",
            (query_text, query_type, result_count, latency_ms),
        )
        conn.commit()
        return {"status": "logged"}
    finally:
        conn.close()


@app.get("/telemetry", response_model=list)
async def get_telemetry(limit: int = 50):
    """Get telemetry report."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT query_type, COUNT(*) as count,
                      AVG(response_time_ms) as avg_latency,
                      AVG(results_count) as avg_results
               FROM query_telemetry
               GROUP BY query_type
               ORDER BY count DESC
               LIMIT %s""",
            (limit,),
        )
        return cur.fetchall()
    finally:
        conn.close()


# ─── Export ───────────────────────────────────────────────────
@app.get("/export", response_model=dict)
async def export_all(session_id: Optional[str] = None):
    """Export all memory data as JSON."""
    conn = get_mdb()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM memory_entries ORDER BY created_at")
        memories = cur.fetchall()

        cur.execute("SELECT * FROM learned_rules ORDER BY created_at")
        rules = cur.fetchall()

        export = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "memories": memories,
            "rules": rules,
            "total_memories": len(memories),
            "total_rules": len(rules),
        }
        return export
    finally:
        conn.close()


# ─── Ollama management ────────────────────────────────────────
@app.get("/models", response_model=dict)
async def list_ollama_models():
    """List available Ollama models."""
    try:
        resp = urllib.request.urlopen(
            f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags", timeout=10
        )
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e), "models": []}


@app.post("/models/pull", response_model=dict)
async def pull_model(model: str):
    """Pull an Ollama model."""
    url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/pull"
    data = json.dumps({"name": model, "stream": False}).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=600)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


# ─── Qdrant management ────────────────────────────────────────
@app.get("/collections", response_model=dict)
async def list_collections():
    """List Qdrant collections."""
    return qdrant_request("GET", "/collections")


@app.get("/collections/{collection_name}/points", response_model=dict)
async def list_collection_points(collection_name: str, limit: int = 20):
    """List points in a Qdrant collection."""
    return qdrant_request(
        "GET", f"/collections/{collection_name}/points/limit", {"limit": limit}
    )
