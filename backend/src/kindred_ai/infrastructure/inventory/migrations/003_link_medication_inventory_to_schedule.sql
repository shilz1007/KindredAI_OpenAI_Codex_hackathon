-- Inventory owns stock, but references the Health-owned schedule by its stable
-- application identifier. This is deliberately not a cross-database foreign key.
-- The migration runner adds the schedule_id column defensively before this SQL.

UPDATE medication_inventory
SET schedule_id = CASE medication_name
    WHEN 'Metformin' THEN 'demo-schedule-metformin'
    WHEN 'Vitamin D' THEN 'demo-schedule-vitamin-d'
    ELSE NULL
END
WHERE schedule_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_medication_inventory_schedule
    ON medication_inventory (schedule_id)
    WHERE schedule_id IS NOT NULL;
