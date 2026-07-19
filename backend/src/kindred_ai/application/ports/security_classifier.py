"""Model boundary for simulated phone-message analysis."""

from typing import Literal, Protocol
from pydantic import BaseModel, ConfigDict


class PhoneMessageClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    risk_level: Literal["low", "medium", "high", "critical"]
    malicious_intent: bool
    explanation: str
    signals: list[str]


class SecurityClassifier(Protocol):
    def classify(self, message: str) -> PhoneMessageClassification: ...
