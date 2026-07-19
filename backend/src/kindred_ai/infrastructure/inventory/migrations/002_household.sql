CREATE TABLE IF NOT EXISTS household_items (
    id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL UNIQUE,
    quantity_available INTEGER NOT NULL,
    reorder_threshold INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS household_purchase_requests (
    id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    status TEXT NOT NULL
);
INSERT OR IGNORE INTO household_items VALUES ('household-tea','Jasmine tea',1,2);
INSERT OR IGNORE INTO household_items VALUES ('household-milk','Milk',3,2);
