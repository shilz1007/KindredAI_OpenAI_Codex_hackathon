"""Pure domain models for Security MCP."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SecurityEvent:
    """A message analyzed for potential safety or fraud signals."""

    id: str
    message: str
    risk_level: str
    matched_signals: tuple[str, ...]
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id, "message": self.message, "risk_level": self.risk_level,
            "matched_signals": list(self.matched_signals), "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SecurityAlert:
    """An actionable alert associated with a recorded security event."""

    id: str
    event_id: str
    severity: str
    status: str
    created_at: datetime

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id, "event_id": self.event_id, "severity": self.severity,
            "status": self.status, "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class PhoneMessage:
    """A simulated incoming phone/SMS message owned by Security MCP."""

    id: str
    message: str
    received_at: datetime
    analysis_status: str
    risk_level: str | None
    explanation: str | None
    signals: tuple[str, ...]
    security_event_id: str | None

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "message": self.message, "received_at": self.received_at.isoformat(), "analysis_status": self.analysis_status, "risk_level": self.risk_level, "explanation": self.explanation, "signals": list(self.signals), "security_event_id": self.security_event_id}
