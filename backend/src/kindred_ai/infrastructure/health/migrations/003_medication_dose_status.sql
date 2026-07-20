CREATE TABLE IF NOT EXISTS medication_dose_status_records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES health_users(id),
    schedule_id TEXT NOT NULL REFERENCES medication_schedules(id),
    scheduled_date TEXT NOT NULL,
    scheduled_time TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('missed')),
    recorded_at TEXT NOT NULL,
    note TEXT,
    UNIQUE (user_id, schedule_id, scheduled_date, scheduled_time)
);

CREATE INDEX IF NOT EXISTS idx_medication_dose_status_user_date
    ON medication_dose_status_records (user_id, scheduled_date);
