"""Swagger-visible HTTP adapter for Inventory MCP use cases."""

from datetime import date

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from kindred_ai.application.inventory.service import get_inventory_service

router = APIRouter(prefix="/inventory", tags=["Inventory MCP"])


class PurchaseRequestBody(BaseModel):
    medication_name: str = Field(examples=["Metformin"])
    quantity: int = Field(ge=1, examples=[60])
    user_confirmed: bool = Field(examples=[True])


class MedicationInventorySetupRequest(BaseModel):
    """Current medicine stock linked to a Health medication schedule."""

    schedule_id: str = Field(min_length=1, examples=["demo-schedule-metformin"])
    medication_name: str = Field(min_length=1, examples=["Metformin"])
    units_available: int = Field(ge=0, examples=[60])
    last_purchased_on: date = Field(examples=["2026-07-20"])


@router.get("")
def check_inventory() -> list[dict[str, str | int]]:
    return [item.to_dict() for item in get_inventory_service().check_inventory()]


@router.post("/medication-stock", status_code=status.HTTP_201_CREATED)
def upsert_medication_inventory(payload: MedicationInventorySetupRequest) -> dict[str, str | int | None]:
    """Create or update local medication stock for one Health schedule."""
    try:
        return get_inventory_service().upsert_medication_inventory(**payload.model_dump()).to_dict()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.post("/purchase-requests", status_code=status.HTTP_201_CREATED)
def request_purchase(payload: PurchaseRequestBody) -> dict[str, str | int]:
    try:
        return get_inventory_service().request_purchase(**payload.model_dump()).to_dict()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
