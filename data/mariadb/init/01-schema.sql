-- ============================================================
-- KILO CORTEX — MariaDB Schema
-- 14 tables for the full memory system
-- ============================================================

CREATE DATABASE IF NOT EXISTS kilo
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE kilo;

-- ─── 1. memory_entries ──────────────────────────────────────
-- Core memory storage (L2/semantic index target)
CREATE TABLE IF NOT EXISTS memory_entries (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    content       TEXT         NOT NULL,
    embedding_id  VARCHAR(255) DEFAULT NULL,
    category      VARCHAR(100) DEFAULT 'general',
    tags          JSON         DEFAULT NULL,
    quality_score  DECIMAL(3,2) DEFAULT 1.00,
    strength      DECIMAL(5,2) DEFAULT 100.00,
    decay_rate    DECIMAL(5,2) DEFAULT 0.01,
    last_retrieved TIMESTAMP    DEFAULT NULL,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    metadata_json JSON         DEFAULT NULL,
    INDEX idx_category (category),
    INDEX idx_quality (quality_score),
    INDEX idx_created (created_at),
    INDEX idx_embedding (embedding_id(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 2. learned_rules ───────────────────────────────────────
-- Rules the agent has learned over time
CREATE TABLE IF NOT EXISTS learned_rules (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    rule_type   VARCHAR(100) NOT NULL,
    pattern     TEXT         NOT NULL,
    action      TEXT         NOT NULL,
    confidence  DECIMAL(3,2) DEFAULT 0.00,
    triggered_count INT      DEFAULT 0,
    last_triggered TIMESTAMP DEFAULT NULL,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    metadata_json JSON       DEFAULT NULL,
    INDEX idx_type (rule_type),
    INDEX idx_confidence (confidence),
    INDEX idx_triggered (triggered_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 3. sessions ────────────────────────────────────────────
-- Agent interaction sessions
CREATE TABLE IF NOT EXISTS sessions (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id  VARCHAR(255) NOT NULL,
    user_id     VARCHAR(255) DEFAULT NULL,
    start_time  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    end_time    TIMESTAMP    DEFAULT NULL,
    messages    JSON         DEFAULT NULL,
    context_json JSON        DEFAULT NULL,
    duration_sec INT          DEFAULT 0,
    INDEX idx_session (session_id),
    INDEX idx_user (user_id),
    INDEX idx_start (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 4. pattern_triggers ────────────────────────────────────
-- Trigger patterns for automatic memory actions
CREATE TABLE IF NOT EXISTS pattern_triggers (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    pattern     TEXT         NOT NULL,
    action      VARCHAR(100) NOT NULL,
    params      JSON         DEFAULT NULL,
    enabled     TINYINT(1)   DEFAULT 1,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 5. memory_quality_report ───────────────────────────────
-- Quality metrics for stored memories
CREATE TABLE IF NOT EXISTS memory_quality_report (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    memory_id       BIGINT UNSIGNED NOT NULL,
    clarity_score   DECIMAL(3,2) DEFAULT 0.00,
    specificity     DECIMAL(3,2) DEFAULT 0.00,
    novelty_score   DECIMAL(3,2) DEFAULT 0.00,
    relevance_score DECIMAL(3,2) DEFAULT 0.00,
    assessed_by     VARCHAR(100) DEFAULT 'auto',
    assessed_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    notes           TEXT         DEFAULT NULL,
    INDEX idx_memory (memory_id),
    INDEX idx_assessed (assessed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 6. discovery_cache ─────────────────────────────────────
-- Cached discovery results
CREATE TABLE IF NOT EXISTS discovery_cache (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    query_hash  CHAR(64)    NOT NULL,
    query_text  TEXT        NOT NULL,
    result_json JSON        DEFAULT NULL,
    created_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP   DEFAULT NULL,
    hits        INT         DEFAULT 0,
    INDEX idx_hash (query_hash),
    INDEX idx_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 7. query_telemetry ─────────────────────────────────────
-- Query performance and usage tracking
CREATE TABLE IF NOT EXISTS query_telemetry (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    query_text      TEXT        NOT NULL,
    query_type      VARCHAR(100) DEFAULT 'search',
    response_time_ms INT         DEFAULT 0,
    results_count   INT         DEFAULT 0,
    user_id         VARCHAR(255) DEFAULT NULL,
    success         TINYINT(1)  DEFAULT 1,
    error_message   TEXT        DEFAULT NULL,
    created_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (query_type),
    INDEX idx_created (created_at),
    INDEX idx_success (success)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 8. memory_ingest_log ───────────────────────────────────
-- Logging memory ingestion events
CREATE TABLE IF NOT EXISTS memory_ingest_log (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source          VARCHAR(255) NOT NULL,
    content_hash    CHAR(64)   NOT NULL,
    content_preview TEXT       DEFAULT NULL,
    status          VARCHAR(50) DEFAULT 'pending',
    memory_id       BIGINT UNSIGNED DEFAULT NULL,
    error_message   TEXT       DEFAULT NULL,
    created_at      TIMESTAMP  DEFAULT CURRENT_TIMESTAMP,
    processed_at    TIMESTAMP  DEFAULT NULL,
    INDEX idx_source (source),
    INDEX idx_status (status),
    INDEX idx_hash (content_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 9. pending_ingest ──────────────────────────────────────
-- Queue for pending memory ingestion
CREATE TABLE IF NOT EXISTS pending_ingest (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    content     TEXT         NOT NULL,
    source      VARCHAR(255) NOT NULL,
    priority    INT          DEFAULT 5,
    status      VARCHAR(50)  DEFAULT 'queued',
    retry_count INT          DEFAULT 0,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_priority (priority, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 10. hebbian_links ──────────────────────────────────────
-- Hebbian associative memory links
CREATE TABLE IF NOT EXISTS hebbian_links (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_id   BIGINT UNSIGNED NOT NULL,
    target_id   BIGINT UNSIGNED NOT NULL,
    strength    DECIMAL(5,2) DEFAULT 1.00,
    last_fire   TIMESTAMP    DEFAULT NULL,
    fire_count  INT          DEFAULT 0,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_link (source_id, target_id),
    INDEX idx_source (source_id),
    INDEX idx_target (target_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 11. feedback_log ───────────────────────────────────────
-- User feedback on memory quality
CREATE TABLE IF NOT EXISTS feedback_log (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    memory_id       BIGINT UNSIGNED DEFAULT NULL,
    query_text      TEXT        DEFAULT NULL,
    rating          TINYINT    DEFAULT NULL,
    feedback_text   TEXT        DEFAULT NULL,
    user_id         VARCHAR(255) DEFAULT NULL,
    created_at      TIMESTAMP  DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_memory (memory_id),
    INDEX idx_rating (rating),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 12. decay_log ──────────────────────────────────────────
-- Memory decay tracking
CREATE TABLE IF NOT EXISTS decay_log (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    memory_id       BIGINT UNSIGNED NOT NULL,
    original_strength DECIMAL(5,2) NOT NULL,
    current_strength  DECIMAL(5,2) NOT NULL,
    decay_amount    DECIMAL(5,2) NOT NULL,
    decay_type      VARCHAR(100) DEFAULT 'time',
    logged_at       TIMESTAMP  DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_memory (memory_id),
    INDEX idx_logged (logged_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 13. decision_log ───────────────────────────────────────
-- Agent decision tracking
CREATE TABLE IF NOT EXISTS decision_log (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id      VARCHAR(255) DEFAULT NULL,
    decision_type   VARCHAR(100) NOT NULL,
    input_summary   TEXT       DEFAULT NULL,
    decision_made   TEXT       NOT NULL,
    confidence      DECIMAL(3,2) DEFAULT 0.00,
    outcome         TEXT       DEFAULT NULL,
    outcome_known   TINYINT(1) DEFAULT 0,
    created_at      TIMESTAMP  DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_type (decision_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 14. failure_events ─────────────────────────────────────
-- Failure and error tracking
CREATE TABLE IF NOT EXISTS failure_events (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    service         VARCHAR(100) NOT NULL,
    error_type      VARCHAR(100) NOT NULL,
    error_message   TEXT         NOT NULL,
    context_json    JSON         DEFAULT NULL,
    resolved        TINYINT(1)   DEFAULT 0,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    resolved_at     TIMESTAMP    DEFAULT NULL,
    INDEX idx_service (service),
    INDEX idx_type (error_type),
    INDEX idx_resolved (resolved),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── 15. config_changes ─────────────────────────────────────
-- Configuration change audit log
CREATE TABLE IF NOT EXISTS config_changes (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    changed_by      VARCHAR(255) DEFAULT NULL,
    config_key      VARCHAR(255) NOT NULL,
    old_value       TEXT       DEFAULT NULL,
    new_value       TEXT       DEFAULT NULL,
    reason          TEXT       DEFAULT NULL,
    created_at      TIMESTAMP  DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_key (config_key),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
