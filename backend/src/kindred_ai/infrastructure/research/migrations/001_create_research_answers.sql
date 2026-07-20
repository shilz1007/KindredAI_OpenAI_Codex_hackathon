CREATE TABLE research_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    provider TEXT NOT NULL,
    researched_at TEXT NOT NULL
);

CREATE INDEX idx_research_answers_researched_at
    ON research_answers (researched_at DESC, id DESC);

