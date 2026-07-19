"""Use cases for the Security MCP MVP."""

from datetime import UTC, datetime
from functools import lru_cache
from uuid import uuid4

from kindred_ai.application.ports.security_repository import SecurityRepository
from kindred_ai.application.ports.security_classifier import SecurityClassifier
from kindred_ai.domain.security import PhoneMessage, SecurityAlert, SecurityEvent
from kindred_ai.infrastructure.security.sqlite_repository import SqliteSecurityRepository
from kindred_ai.infrastructure.openai.security_classifier import OpenAISecurityClassifier
from kindred_ai.config.model_settings import get_model_settings

MAX_EVENT_LIMIT = 100
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
HIGH_RISK_SIGNALS = (
    "gift card", "password", "pin", "one-time code", "otp", "remote access",
    "verification code", "share the code", "code sent",
)
MEDIUM_RISK_SIGNALS = ("urgent", "bank account", "click this link", "send money")


class SecurityService:
    """Coordinates deterministic demo safety analysis and security persistence."""

    def __init__(self, repository: SecurityRepository, classifier: SecurityClassifier | None = None) -> None:
        self._repository = repository
        self._classifier = classifier

    def receive_phone_message(self, message: str) -> tuple[PhoneMessage, SecurityAlert | None]:
        if not message.strip():
            raise ValueError("Phone message cannot be empty.")
        phone_message = self._repository.add_phone_message(message_id=str(uuid4()), message=message.strip(), received_at=datetime.now(UTC))
        if self._classifier is None:
            self._repository.fail_phone_message(message_id=phone_message.id)
            raise RuntimeError("Phone-message classifier is not configured.")
        try:
            classification = self._classifier.classify(phone_message.message)
        except Exception as error:
            self._repository.fail_phone_message(message_id=phone_message.id)
            raise RuntimeError("Phone-message analysis failed.") from error
        event_id = None
        alert = None
        if classification.risk_level != "low":
            event = self._repository.add_event(event_id=str(uuid4()), message=phone_message.message, risk_level=classification.risk_level, matched_signals=tuple(classification.signals), created_at=datetime.now(UTC))
            event_id = event.id
            alert = self.create_security_alert(event_id=event.id, severity=classification.risk_level)
        return self._repository.complete_phone_message(message_id=phone_message.id, risk_level=classification.risk_level, explanation=classification.explanation, signals=tuple(classification.signals), event_id=event_id), alert

    def get_phone_messages(self, *, limit: int) -> list[PhoneMessage]:
        if not 1 <= limit <= MAX_EVENT_LIMIT: raise ValueError(f"Event limit must be between 1 and {MAX_EVENT_LIMIT}.")
        return self._repository.get_phone_messages(limit)

    def analyze_message(self, message: str) -> SecurityEvent:
        """Record a message with transparent keyword-based risk classification.

        TODO: Replace this MVP heuristic with an approved policy/model integration.
        """
        if not message.strip():
            raise ValueError("Message cannot be empty.")
        normalized = message.lower()
        high_matches = tuple(signal for signal in HIGH_RISK_SIGNALS if signal in normalized)
        medium_matches = tuple(signal for signal in MEDIUM_RISK_SIGNALS if signal in normalized)
        signals = high_matches + medium_matches
        risk_level = "high" if high_matches else "medium" if medium_matches else "low"
        return self._repository.add_event(
            event_id=str(uuid4()), message=message.strip(), risk_level=risk_level,
            matched_signals=signals, created_at=datetime.now(UTC),
        )

    def create_security_alert(self, *, event_id: str, severity: str) -> SecurityAlert:
        """Create an open alert for a known security event."""
        if severity not in VALID_SEVERITIES:
            raise ValueError("Alert severity must be low, medium, high, or critical.")
        if self._repository.get_event(event_id) is None:
            raise ValueError("Security event was not found.")
        return self._repository.add_alert(
            alert_id=str(uuid4()), event_id=event_id, severity=severity,
            status="open", created_at=datetime.now(UTC),
        )

    def get_security_events(self, *, limit: int) -> list[SecurityEvent]:
        """Return recorded events, newest first."""
        if not 1 <= limit <= MAX_EVENT_LIMIT:
            raise ValueError(f"Event limit must be between 1 and {MAX_EVENT_LIMIT}.")
        return self._repository.get_events(limit)


@lru_cache(maxsize=1)
def get_security_service() -> SecurityService:
    """Create and initialize the configured Security MCP service once per process."""
    repository = SqliteSecurityRepository.from_environment()
    repository.initialize()
    settings = get_model_settings()
    return SecurityService(repository, OpenAISecurityClassifier(api_key=settings.api_key, model=settings.agents_model))


def initialize_security_service() -> None:
    """Eagerly initialize Security MCP persistence during application startup."""
    get_security_service()
