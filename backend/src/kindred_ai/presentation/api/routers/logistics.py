"""Swagger-visible adapter for Logistics Agent household workflows."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from kindred_ai.application.logistics import get_logistics_agent

router = APIRouter(prefix="/logistics", tags=["Logistics Agent"])


class HouseholdPurchaseBody(BaseModel):
    item_name: str = Field(min_length=1, examples=["Jasmine tea"])
    quantity: int = Field(ge=1, examples=[2])
    user_confirmed: bool = Field(examples=[True])


class ReminderBody(BaseModel):
    title: str = Field(min_length=1, examples=["Buy Jasmine tea"])
    remind_at: datetime = Field(examples=["2026-07-26T09:00:00+02:00"])


@router.get("/household-inventory")
def household_inventory() -> list[dict[str, object]]:
    return get_logistics_agent().household_inventory()


@router.post("/purchase-requests", status_code=status.HTTP_201_CREATED)
def request_purchase(payload: HouseholdPurchaseBody) -> dict[str, object]:
    try:
        return get_logistics_agent().request_purchase(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.post("/reminders", status_code=status.HTTP_201_CREATED)
def create_reminder(payload: ReminderBody) -> dict[str, str]:
    try:
        return get_logistics_agent().schedule_reminder(title=payload.title, remind_at=payload.remind_at.isoformat())
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
