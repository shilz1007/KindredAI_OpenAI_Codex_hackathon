"""Pure domain models for medication and household inventory."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MedicationInventory:
    id: str
    medication_name: str
    units_available: int
    last_purchased_at: datetime
    schedule_id: str | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        return {"id": self.id, "schedule_id": self.schedule_id, "medication_name": self.medication_name, "units_available": self.units_available, "last_purchased_at": self.last_purchased_at.isoformat()}


@dataclass(frozen=True, slots=True)
class PurchaseRequest:
    id: str
    medication_name: str
    quantity: int
    status: str
    created_at: datetime

    def to_dict(self) -> dict[str, str | int]:
        return {"id": self.id, "medication_name": self.medication_name, "quantity": self.quantity, "status": self.status, "created_at": self.created_at.isoformat()}


@dataclass(frozen=True, slots=True)
class HouseholdItem:
    """A non-medication item owned by the Logistics workflow."""

    id: str
    item_name: str
    quantity_available: int
    reorder_threshold: int

    @property
    def reorder_needed(self) -> bool:
        return self.quantity_available <= self.reorder_threshold

    def to_dict(self) -> dict[str, str | int | bool]:
        return {
            "id": self.id,
            "item_name": self.item_name,
            "quantity_available": self.quantity_available,
            "reorder_threshold": self.reorder_threshold,
            "reorder_needed": self.reorder_needed,
        }


@dataclass(frozen=True, slots=True)
class HouseholdPurchaseRequest:
    id: str
    item_name: str
    quantity: int
    status: str
    created_at: datetime

    def to_dict(self) -> dict[str, str | int]:
        return {"id": self.id, "item_name": self.item_name, "quantity": self.quantity, "status": self.status, "created_at": self.created_at.isoformat()}


@dataclass(frozen=True, slots=True)
class Reminder:
    id: str
    title: str
    remind_at: datetime
    status: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "title": self.title, "remind_at": self.remind_at.isoformat(), "status": self.status}
