"""Swagger-visible HTTP adapter for Inventory MCP use cases."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from kindred_ai.application.inventory.service import get_inventory_service

router = APIRouter(prefix="/inventory", tags=["Inventory MCP"])


class PurchaseRequestBody(BaseModel):
    medication_name: str = Field(examples=["Metformin"])
    quantity: int = Field(ge=1, examples=[60])
    user_confirmed: bool = Field(examples=[True])


@router.get("")
def check_inventory() -> list[dict[str, str | int]]:
    return [item.to_dict() for item in get_inventory_service().check_inventory()]


@router.post("/purchase-requests", status_code=status.HTTP_201_CREATED)
def request_purchase(payload: PurchaseRequestBody) -> dict[str, str | int]:
    try:
        return get_inventory_service().request_purchase(**payload.model_dump()).to_dict()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
