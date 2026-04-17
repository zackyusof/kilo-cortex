#!/bin/bash
# ============================================================
# KILO CORTEX — Bootstrap Script
# Runs once to initialize all services after first start
# ============================================================
set -euo pipefail

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     KILO CORTEX — Bootstrap Initialization              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ─── Wait for services ─────────────────────────────────────
wait_for_service() {
    local name="$1"
    local cmd="$2"
    local max_wait="${3:-60}"
    echo "  ⏳ Waiting for ${name}..."
    for i in $(seq 1 $max_wait); do
        if eval "$cmd" > /dev/null 2>&1; then
            echo "  ✅ ${name} is ready"
            return 0
        fi
        sleep 2
    done
    echo "  ❌ ${name} did not become ready in ${max_wait}s"
    return 1
}

wait_for_service "MariaDB" "python3 -c \"
import pymysql
conn = pymysql.connect(host='${MARIADB_HOST}', port=${MARIADB_PORT},
    user='${MARIADB_USER}', password='${MARIADB_PASSWORD}',
    database='${MARIADB_DATABASE}', connect_timeout=5)
conn.close()
\"" 120

wait_for_service "Redis" "python3 -c \"
import redis
conn = redis.Redis(host='${REDIS_HOST}', port=${REDIS_PORT},
    password='${REDIS_PASSWORD}', decode_responses=True, socket_timeout=5)
conn.ping()
conn.close()
\"" 30

wait_for_service "Qdrant" "python3 -c \"
import urllib.request
urllib.request.urlopen('http://${QDRANT_HOST}:${QDRANT_PORT}/health', timeout=5).read()
\"" 30

wait_for_service "Ollama" "python3 -c \"
import urllib.request
urllib.request.urlopen('http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags', timeout=5).read()
\"" 30

echo ""
echo "  📦 All services are healthy. Running bootstrap..."
echo ""

# ─── 1. Create database and user ──────────────────────────
echo "  [1/4] Initializing database..."
python3 -c "
import pymysql
conn = pymysql.connect(
    host='${MARIADB_HOST}', port=${MARIADB_PORT},
    user='root', password='${MARIADB_ROOT_PASSWORD}'
)
cursor = conn.cursor()
cursor.execute('CREATE DATABASE IF NOT EXISTS ${MARIADB_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
cursor.execute('CREATE USER IF NOT EXISTS \`${MARIADB_USER}\`@% IDENTIFIED BY \`${MARIADB_PASSWORD}\`')
cursor.execute('GRANT ALL PRIVILEGES ON \`${MARIADB_DATABASE}\`.* TO \`${MARIADB_USER}\`@%')
cursor.execute('FLUSH PRIVILEGES')
conn.commit()
conn.close()
print('  ✅ Database and user created')
"

# ─── 2. Create Qdrant collections ──────────────────────────
echo "  [2/4] Creating Qdrant collections..."
python3 -c "
import urllib.request, json

QDRANT_HOST = '${QDRANT_HOST}'
QDRANT_PORT = '${QDRANT_PORT}'
QDRANT_API_KEY = '${QDRANT_API_KEY}'
GPU_MODE = '${GPU_MODE}'.lower() == 'true'

headers = {
    'Content-Type': 'application/json',
    'accept': 'application/json',
}
if QDRANT_API_KEY:
    headers['x-api-key'] = QDRANT_API_KEY

def qdrant_request(method, path, data=None):
    url = f'http://{QDRANT_HOST}:{QDRANT_PORT}{path}'
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
        headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        print(f'  ⚠️  Qdrant request failed: {e}')
        return None

# Get existing collections
collections = qdrant_request('GET', '/collections')
existing_collections = [c['name'] for c in collections.get('collections', [])] if collections else []

# Collection 1: learned-rules (384-dim)
rule_collection = 'kilo-learned-rules'
if rule_collection not in existing_collections:
    qdrant_request('PUT', f'/collections/{rule_collection}', {
        'vectors': {'size': 384, 'distance': 'Cosine'}
    })
    print(f'  ✅ Created collection: {rule_collection} (384-dim)')
else:
    print(f'  ⏭️  Collection exists: {rule_collection}')

# Collection 2: session-history (384-dim)
session_collection = 'kilo-session-history'
if session_collection not in existing_collections:
    qdrant_request('PUT', f'/collections/{session_collection}', {
        'vectors': {'size': 384, 'distance': 'Cosine'}
    })
    print(f'  ✅ Created collection: {session_collection} (384-dim)')
else:
    print(f'  ⏭️  Collection exists: {session_collection}')

# Collection 3: mysql-project (768-dim for GPU, 384-dim for CPU)
project_collection = 'mysql-project'
dims = 768 if GPU_MODE else 384
if project_collection not in existing_collections:
    qdrant_request('PUT', f'/collections/{project_collection}', {
        'vectors': {'size': dims, 'distance': 'Cosine'}
    })
    print(f'  ✅ Created collection: {project_collection} ({dims}-dim)')
else:
    print(f'  ⏭️  Collection exists: {project_collection}')
"

# ─── 3. Download embedding model ──────────────────────────
echo "  [3/4] Downloading embedding model: ${EMBEDDING_MODEL}..."
python3 -c "
import urllib.request, json

OLLAMA_HOST = '${OLLAMA_HOST}'
OLLAMA_PORT = '${OLLAMA_PORT}'
MODEL = '${EMBEDDING_MODEL}'

# Check if model already exists
url = f'http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags'
req = urllib.request.Request(url, method='GET')
resp = urllib.request.urlopen(req, timeout=10)
tags = json.loads(resp.read())
existing = [m['name'].split(':')[0] for m in tags.get('models', [])]

if MODEL not in existing:
    print(f'  ⏳ Pulling {MODEL} (this may take a while)...')
    pull_url = f'http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/pull'
    pull_data = json.dumps({'name': MODEL, 'stream': False}).encode()
    pull_req = urllib.request.Request(pull_url, data=pull_data,
        headers={'Content-Type': 'application/json'}, method='POST')
    pull_resp = urllib.request.urlopen(pull_req, timeout=600)
    result = json.loads(pull_resp.read())
    if result.get('status') == 'success' or 'pulling' in str(result).lower():
        print(f'  ✅ Model {MODEL} downloaded')
    else:
        print(f'  ⚠️  Model download status: {result}')
else:
    print(f'  ⏭️  Model {MODEL} already available')
"

# ─── 4. Seed pattern triggers ──────────────────────────────
echo "  [4/4] Seeding pattern triggers..."
python3 -c "
import pymysql

conn = pymysql.connect(
    host='${MARIADB_HOST}', port=${MARIADB_PORT},
    user='${MARIADB_USER}', password='${MARIADB_PASSWORD}',
    database='${MARIADB_DATABASE}'
)
cursor = conn.cursor()

triggers = [
    ('high_confidence_rule', '%confidence%>0.9%', 'store_as_rule', '{\"min_confidence\": 0.9}', 1),
    ('error_pattern', '%error% OR %fail%', 'log_failure', '{\"auto_log\": true}', 1),
    ('decision_made', '%decided% OR %chose%', 'log_decision', '{\"auto_log\": true}', 1),
    ('session_boundary', '%session complete% OR %task done%', 'close_session', '{\"archive\": true}', 1),
    ('feedback_received', '%rating% OR %good% OR %bad%', 'store_feedback', '{\"auto_rate\": true}', 1),
    ('repeated_mention', None, 'increment_hebbian', '{\"threshold\": 5}', 1),
    ('novel_discovery', None, 'flag_novel', '{\"auto_assess\": true}', 1),
    ('config_change', '%config% OR %setting%', 'log_config_change', '{\"audit\": true}', 1),
]

for name, pattern, action, params, enabled in triggers:
    cursor.execute(
        'SELECT COUNT(*) FROM pattern_triggers WHERE name = %s', (name,)
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            'INSERT INTO pattern_triggers (name, pattern, action, params, enabled) VALUES (%s, %s, %s, %s, %s)',
            (name, pattern, action, params, enabled)
        )

conn.commit()
print(f'  ✅ Pattern triggers seeded')
conn.close()
"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Bootstrap complete! All services are ready.         ║"
echo "║     Memory API: http://localhost:8088                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
