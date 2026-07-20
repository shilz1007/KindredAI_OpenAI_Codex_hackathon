"""SQLite implementation of the Inventory MCP persistence port."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from kindred_ai.domain.inventory import HouseholdItem, HouseholdPurchaseRequest, MedicationInventory, PurchaseRequest, Reminder

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[4] / "data" / "inventory.sqlite3"
MIGRATIONS_PATH = Path(__file__).with_name("migrations")


class SqliteInventoryRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @classmethod
    def from_environment(cls) -> "SqliteInventoryRepository":
        path = os.getenv("KINDRED_INVENTORY_DB_PATH")
        return cls(Path(path) if path else DEFAULT_DATABASE_PATH)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            applied = {row["version"] for row in connection.execute("SELECT version FROM schema_migrations")}
            for migration in sorted(MIGRATIONS_PATH.glob("*.sql")):
                if migration.name not in applied:
                    if migration.name == "003_link_medication_inventory_to_schedule.sql":
                        columns = {row["name"] for row in connection.execute("PRAGMA table_info(medication_inventory)")}
                        if "schedule_id" not in columns:
                            connection.execute("ALTER TABLE medication_inventory ADD COLUMN schedule_id TEXT")
                    connection.executescript(migration.read_text(encoding="utf-8"))
                    connection.execute("INSERT INTO schema_migrations VALUES (?, ?)", (migration.name, datetime.now(UTC).isoformat()))
            for item in (
                ("demo-inventory-metformin", "demo-schedule-metformin", "Metformin", 12, "2026-07-10T09:00:00+00:00"),
                ("demo-inventory-vitamin-d", "demo-schedule-vitamin-d", "Vitamin D", 30, "2026-07-10T09:00:00+00:00"),
            ):
                connection.execute(
                    """INSERT OR IGNORE INTO medication_inventory
                    (id, schedule_id, medication_name, units_available, last_purchased_at)
                    VALUES (?, ?, ?, ?, ?)""",
                    item,
                )

    def get_inventory(self) -> list[MedicationInventory]:
        with self._connection() as connection:
            rows = connection.execute("SELECT id, schedule_id, medication_name, units_available, last_purchased_at FROM medication_inventory ORDER BY medication_name").fetchall()
        return [_item(row) for row in rows]

    def get_item(self, medication_name: str) -> MedicationInventory | None:
        with self._connection() as connection:
            row = connection.execute("SELECT id, schedule_id, medication_name, units_available, last_purchased_at FROM medication_inventory WHERE medication_name = ?", (medication_name,)).fetchone()
        return _item(row) if row else None

    def get_item_for_schedule(self, schedule_id: str) -> MedicationInventory | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, schedule_id, medication_name, units_available, last_purchased_at FROM medication_inventory WHERE schedule_id = ?",
                (schedule_id,),
            ).fetchone()
        return _item(row) if row else None

    def upsert_medication_inventory(
        self,
        *,
        inventory_id: str,
        schedule_id: str,
        medication_name: str,
        units_available: int,
        last_purchased_at: datetime,
    ) -> MedicationInventory:
        """Create or replace stock associated with one Health schedule ID."""
        timestamp = last_purchased_at.astimezone(UTC).isoformat()
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT id FROM medication_inventory WHERE schedule_id = ?", (schedule_id,)
            ).fetchone()
            if existing:
                connection.execute(
                    """UPDATE medication_inventory
                    SET medication_name = ?, units_available = ?, last_purchased_at = ?
                    WHERE schedule_id = ?""",
                    (medication_name, units_available, timestamp, schedule_id),
                )
                inventory_id = existing["id"]
            else:
                connection.execute(
                    """INSERT INTO medication_inventory
                    (id, schedule_id, medication_name, units_available, last_purchased_at)
                    VALUES (?, ?, ?, ?, ?)""",
                    (inventory_id, schedule_id, medication_name, units_available, timestamp),
                )
        return MedicationInventory(inventory_id, medication_name, units_available, datetime.fromisoformat(timestamp), schedule_id)

    def add_purchase_request(self, *, request_id: str, medication_name: str, quantity: int, created_at: datetime) -> PurchaseRequest:
        timestamp = created_at.astimezone(UTC).isoformat()
        with self._connection() as connection:
            connection.execute("INSERT INTO purchase_requests VALUES (?, ?, ?, 'requested', ?)", (request_id, medication_name, quantity, timestamp))
        return PurchaseRequest(request_id, medication_name, quantity, "requested", datetime.fromisoformat(timestamp))

    def get_household_inventory(self) -> list[HouseholdItem]:
        with self._connection() as connection:
            rows = connection.execute("SELECT id, item_name, quantity_available, reorder_threshold FROM household_items ORDER BY item_name").fetchall()
        return [_household_item(row) for row in rows]

    def get_household_item(self, item_name: str) -> HouseholdItem | None:
        with self._connection() as connection:
            row = connection.execute("SELECT id, item_name, quantity_available, reorder_threshold FROM household_items WHERE lower(item_name) = lower(?)", (item_name,)).fetchone()
        return _household_item(row) if row else None

    def add_household_purchase_request(self, *, request_id: str, item_name: str, quantity: int, created_at: datetime) -> HouseholdPurchaseRequest:
        timestamp = created_at.astimezone(UTC).isoformat()
        with self._connection() as connection:
            connection.execute("INSERT INTO household_purchase_requests VALUES (?, ?, ?, 'requested', ?)", (request_id, item_name, quantity, timestamp))
        return HouseholdPurchaseRequest(request_id, item_name, quantity, "requested", datetime.fromisoformat(timestamp))

    def add_reminder(self, *, reminder_id: str, title: str, remind_at: datetime) -> Reminder:
        timestamp = remind_at.astimezone(UTC).isoformat()
        with self._connection() as connection:
            connection.execute("INSERT INTO reminders VALUES (?, ?, ?, 'scheduled')", (reminder_id, title, timestamp))
        return Reminder(reminder_id, title, datetime.fromisoformat(timestamp), "scheduled")

    def get_reminders(self) -> list[Reminder]:
        """Return local scheduled reminders in their next-due order."""
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT id, title, remind_at, status FROM reminders
                WHERE status = 'scheduled' ORDER BY remind_at ASC, id ASC"""
            ).fetchall()
        return [
            Reminder(row["id"], row["title"], datetime.fromisoformat(row["remind_at"]), row["status"])
            for row in rows
        ]


def _item(row: sqlite3.Row) -> MedicationInventory:
    return MedicationInventory(row["id"], row["medication_name"], row["units_available"], datetime.fromisoformat(row["last_purchased_at"]), row["schedule_id"])


def _household_item(row: sqlite3.Row) -> HouseholdItem:
    return HouseholdItem(row["id"], row["item_name"], row["quantity_available"], row["reorder_threshold"])
