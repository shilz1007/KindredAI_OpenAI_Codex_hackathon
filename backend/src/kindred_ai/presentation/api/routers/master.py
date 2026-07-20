"""Browser-facing API for Master Agent text conversations."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from kindred_ai.application.master import get_master_agent

router = APIRouter(prefix="/master", tags=["Master Agent"])


class ConversationTurnRequest(BaseModel):
    message: str = Field(min_length=1, examples=["How many days of Metformin do I have left?"])


@router.post("/welcome-thought", status_code=status.HTTP_201_CREATED)
def welcome_thought() -> dict[str, str]:
    """Generate one short, fresh Care Hub encouragement for the current local login."""
    try:
        return {"thought": get_master_agent().welcome_thought()}
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.post("/conversations/{session_id}/turns", status_code=status.HTTP_201_CREATED)
def send_turn(session_id: str, payload: ConversationTurnRequest) -> dict[str, str]:
    """Send an English text turn through Master and its approved specialist delegation."""
    try:
        return {"session_id": session_id, "reply": get_master_agent().respond(payload.message, session_id=session_id)}
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.delete("/conversations/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_conversation(session_id: str) -> None:
    get_master_agent().clear_conversation(session_id)
