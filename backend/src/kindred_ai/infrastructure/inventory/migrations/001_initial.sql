CREATE TABLE IF NOT EXISTS medication_inventory (
    id TEXT PRIMARY KEY,
    medication_name TEXT NOT NULL UNIQUE,
    units_available INTEGER NOT NULL CHECK (units_available >= 0),
    last_purchased_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS purchase_requests (
    id TEXT PRIMARY KEY,
    medication_name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    status TEXT NOT NULL CHECK (status IN ('requested', 'ordered', 'received')),
    created_at TEXT NOT NULL
);
