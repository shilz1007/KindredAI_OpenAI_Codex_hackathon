"""Use cases for the Inventory MCP medication prototype."""

from datetime import UTC, datetime
from functools import lru_cache
from uuid import uuid4

from kindred_ai.application.ports.inventory_repository import InventoryRepository
from kindred_ai.domain.inventory import HouseholdItem, HouseholdPurchaseRequest, MedicationInventory, PurchaseRequest, Reminder
from kindred_ai.infrastructure.inventory.sqlite_repository import SqliteInventoryRepository


class InventoryService:
    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    def check_inventory(self) -> list[MedicationInventory]:
        return self._repository.get_inventory()

    def get_item(self, medication_name: str) -> MedicationInventory | None:
        return self._repository.get_item(medication_name)

    def get_item_for_schedule(self, schedule_id: str) -> MedicationInventory | None:
        return self._repository.get_item_for_schedule(schedule_id)

    def request_purchase(self, *, medication_name: str, quantity: int, user_confirmed: bool) -> PurchaseRequest:
        if not user_confirmed:
            raise ValueError("User confirmation is required before requesting a medication purchase.")
        if quantity < 1:
            raise ValueError("Purchase quantity must be at least 1.")
        if self.get_item(medication_name) is None:
            raise ValueError("Medication is not present in inventory.")
        return self._repository.add_purchase_request(
            request_id=str(uuid4()), medication_name=medication_name, quantity=quantity, created_at=datetime.now(UTC),
        )

    def check_household_inventory(self) -> list[HouseholdItem]:
        """Return Logistics-owned household stock and reorder signals."""
        return self._repository.get_household_inventory()

    def request_household_purchase(self, *, item_name: str, quantity: int, user_confirmed: bool) -> HouseholdPurchaseRequest:
        """Record an explicit, prototype-only household purchase request."""
        if not user_confirmed:
            raise ValueError("User confirmation is required before requesting a household purchase.")
        if quantity < 1:
            raise ValueError("Purchase quantity must be at least 1.")
        item = self._repository.get_household_item(item_name)
        if item is None:
            raise ValueError("Household item is not present in inventory.")
        return self._repository.add_household_purchase_request(
            request_id=str(uuid4()), item_name=item.item_name, quantity=quantity, created_at=datetime.now(UTC),
        )

    def create_reminder(self, *, title: str, remind_at: datetime) -> Reminder:
        """Schedule a local reminder; delivery is intentionally deferred."""
        if not title.strip():
            raise ValueError("Reminder title is required.")
        if remind_at.tzinfo is None:
            raise ValueError("Reminder time must include a timezone.")
        return self._repository.add_reminder(reminder_id=str(uuid4()), title=title.strip(), remind_at=remind_at)


@lru_cache(maxsize=1)
def get_inventory_service() -> InventoryService:
    repository = SqliteInventoryRepository.from_environment()
    repository.initialize()
    return InventoryService(repository)


def initialize_inventory_service() -> None:
    get_inventory_service()
