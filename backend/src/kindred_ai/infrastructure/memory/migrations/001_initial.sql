CREATE TABLE IF NOT EXISTS memory_users (
    id TEXT PRIMARY KEY,
    preferred_name TEXT NOT NULL,
    preferred_language TEXT NOT NULL,
    timezone TEXT NOT NULL,
    preferences TEXT
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES memory_users(id),
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT NOT NULL,
    importance INTEGER NOT NULL CHECK (importance BETWEEN 1 AND 5),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation_history (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES memory_users(id),
    speaker TEXT NOT NULL CHECK (speaker IN ('user', 'assistant')),
    content TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_history_user_occurred
    ON conversation_history (user_id, occurred_at DESC);
