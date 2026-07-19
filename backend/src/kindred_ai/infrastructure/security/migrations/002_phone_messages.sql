CREATE TABLE IF NOT EXISTS phone_messages (
    id TEXT PRIMARY KEY,
    message TEXT NOT NULL,
    received_at TEXT NOT NULL,
    analysis_status TEXT NOT NULL,
    risk_level TEXT,
    explanation TEXT,
    signals TEXT NOT NULL DEFAULT '[]',
    security_event_id TEXT REFERENCES security_events(id)
);
CREATE INDEX IF NOT EXISTS idx_phone_messages_received ON phone_messages (received_at DESC);
