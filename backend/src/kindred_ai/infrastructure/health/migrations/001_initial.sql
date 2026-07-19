CREATE TABLE IF NOT EXISTS health_users (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    timezone TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS medication_schedules (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES health_users(id),
    medication_name TEXT NOT NULL,
    dose_instructions TEXT NOT NULL,
    timezone TEXT NOT NULL,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS medication_schedule_times (
    schedule_id TEXT NOT NULL REFERENCES medication_schedules(id),
    local_time TEXT NOT NULL,
    PRIMARY KEY (schedule_id, local_time)
);

CREATE TABLE IF NOT EXISTS medication_taken_records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES health_users(id),
    schedule_id TEXT NOT NULL REFERENCES medication_schedules(id),
    taken_at TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS health_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES health_users(id),
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    details TEXT,
    severity TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_medication_schedules_user_active
    ON medication_schedules (user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_health_events_user_occurred
    ON health_events (user_id, occurred_at DESC);
