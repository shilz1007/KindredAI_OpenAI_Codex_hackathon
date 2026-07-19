"""Swagger-visible HTTP adapter for Guardian Agent workflows."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from kindred_ai.application.guardian import get_guardian_agent

router = APIRouter(prefix="/guardian", tags=["Guardian Agent"])


class AnalyzeRequest(BaseModel):
    message: str = Field(examples=["Urgent: send your gift card details."])


class ReplenishmentRequest(BaseModel):
    medication_name: str = Field(examples=["Metformin"])
    quantity: int = Field(ge=1, examples=[60])
    user_confirmed: bool = Field(examples=[True])


@router.post("/analyze", status_code=status.HTTP_201_CREATED)
def analyze_message(payload: AnalyzeRequest) -> dict[str, Any]:
    try:
        return get_guardian_agent().analyze_message(payload.message)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.get("/medication-supply")
def medication_supply() -> list[dict[str, Any]]:
    return get_guardian_agent().medication_supply()


@router.post("/replenishment-requests", status_code=status.HTTP_201_CREATED)
def request_replenishment(payload: ReplenishmentRequest) -> dict[str, Any]:
    try:
        return get_guardian_agent().request_medication_replenishment(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
