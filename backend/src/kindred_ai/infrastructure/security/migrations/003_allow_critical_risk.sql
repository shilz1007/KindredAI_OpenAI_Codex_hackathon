-- SQLite cannot alter a CHECK constraint in place. Rebuild the three related
-- tables so GPT-classified `critical` phone messages can be persisted safely.
PRAGMA foreign_keys = OFF;

ALTER TABLE phone_messages RENAME TO phone_messages_legacy;
ALTER TABLE security_alerts RENAME TO security_alerts_legacy;
ALTER TABLE security_events RENAME TO security_events_legacy;

DROP INDEX IF EXISTS idx_phone_messages_received;
DROP INDEX IF EXISTS idx_security_alerts_event;
DROP INDEX IF EXISTS idx_security_events_created;

CREATE TABLE security_events (
    id TEXT PRIMARY KEY,
    message TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    matched_signals TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE security_alerts (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES security_events(id),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL CHECK (status IN ('open', 'resolved')),
    created_at TEXT NOT NULL
);

CREATE TABLE phone_messages (
    id TEXT PRIMARY KEY,
    message TEXT NOT NULL,
    received_at TEXT NOT NULL,
    analysis_status TEXT NOT NULL,
    risk_level TEXT,
    explanation TEXT,
    signals TEXT NOT NULL DEFAULT '[]',
    security_event_id TEXT REFERENCES security_events(id)
);

INSERT INTO security_events (id, message, risk_level, matched_signals, created_at)
SELECT id, message, risk_level, matched_signals, created_at FROM security_events_legacy;

INSERT INTO security_alerts (id, event_id, severity, status, created_at)
SELECT id, event_id, severity, status, created_at FROM security_alerts_legacy;

INSERT INTO phone_messages (id, message, received_at, analysis_status, risk_level, explanation, signals, security_event_id)
SELECT id, message, received_at, analysis_status, risk_level, explanation, signals, security_event_id FROM phone_messages_legacy;

-- Inbox analysis is synchronous in this prototype. Any old `pending` record
-- therefore came from the pre-migration persistence failure and is surfaced
-- honestly instead of appearing to be actively processed.
UPDATE phone_messages SET analysis_status = 'failed' WHERE analysis_status = 'pending';

DROP TABLE phone_messages_legacy;
DROP TABLE security_alerts_legacy;
DROP TABLE security_events_legacy;

CREATE INDEX idx_security_events_created ON security_events (created_at DESC);
CREATE INDEX idx_security_alerts_event ON security_alerts (event_id);
CREATE INDEX idx_phone_messages_received ON phone_messages (received_at DESC);

PRAGMA foreign_keys = ON;
