-- ============================================================
-- KILO CORTEX — Seed Pattern Triggers
-- 8 default patterns for automatic memory actions
-- ============================================================

USE kilo;

INSERT INTO pattern_triggers (name, pattern, action, params, enabled) VALUES
('high_confidence_rule', '%confidence%>0.9%', 'store_as_rule', '{"min_confidence": 0.9}', 1),
('error_pattern', '%error% OR %fail%', 'log_failure', '{"auto_log": true}', 1),
('decision_made', '%decided% OR %chose%', 'log_decision', '{"auto_log": true}', 1),
('session_boundary', '%session complete% OR %task done%', 'close_session', '{"archive": true}', 1),
('feedback_received', '%rating% OR %good% OR %bad%', 'store_feedback', '{"auto_rate": true}', 1),
('repeated_mention', NULL, 'increment_hebbian', '{"threshold": 5}', 1),
('novel_discovery', NULL, 'flag_novel', '{"auto_assess": true}', 1),
('config_change', '%config% OR %setting%', 'log_config_change', '{"audit": true}', 1)
ON DUPLICATE KEY UPDATE name=VALUES(name);
