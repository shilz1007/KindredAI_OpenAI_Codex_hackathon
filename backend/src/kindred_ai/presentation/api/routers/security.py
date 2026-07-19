"""Swagger-visible HTTP adapter for Security MCP use cases."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from kindred_ai.application.security.service import MAX_EVENT_LIMIT, get_security_service

router = APIRouter(prefix="/security", tags=["Security MCP"])


class AnalyzeMessageRequest(BaseModel):
    message: str = Field(examples=["Urgent: send gift card details now."])


class CreateAlertRequest(BaseModel):
    event_id: str = Field(examples=["demo-security-event-scam"])
    severity: Literal["low", "medium", "high", "critical"] = "medium"

class PhoneMessageRequest(BaseModel):
    message: str = Field(examples=["Your bank account is blocked. Send the verification code now."])

@router.post("/phone-messages", status_code=status.HTTP_201_CREATED)
def receive_phone_message(payload: PhoneMessageRequest) -> dict[str, object]:
    """Store and immediately classify a simulated incoming phone/SMS message."""
    try:
        phone_message, alert = get_security_service().receive_phone_message(payload.message)
        return {"phone_message": phone_message.to_dict(), "alert": alert.to_dict() if alert else None}
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

@router.get("/phone-messages")
def get_phone_messages(limit: int = Query(default=20, ge=1, le=MAX_EVENT_LIMIT)) -> list[dict[str, object]]:
    return [message.to_dict() for message in get_security_service().get_phone_messages(limit=limit)]


@router.post("/analyze-message", status_code=status.HTTP_201_CREATED)
def analyze_message(payload: AnalyzeMessageRequest) -> dict[str, object]:
    """Analyze and record a message using the MVP deterministic safety rules."""
    try:
        return get_security_service().analyze_message(payload.message).to_dict()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.post("/alerts", status_code=status.HTTP_201_CREATED)
def create_security_alert(payload: CreateAlertRequest) -> dict[str, str]:
    """Create an open alert for a recorded security event."""
    try:
        return get_security_service().create_security_alert(event_id=payload.event_id, severity=payload.severity).to_dict()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.get("/events")
def get_security_events(limit: int = Query(default=20, ge=1, le=MAX_EVENT_LIMIT)) -> list[dict[str, object]]:
    """Get recorded security events, newest first."""
    return [event.to_dict() for event in get_security_service().get_security_events(limit=limit)]
