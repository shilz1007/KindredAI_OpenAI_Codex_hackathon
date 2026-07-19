"""GPT-5.1 classifier for stored simulated phone messages."""
from openai import OpenAI
from kindred_ai.application.ports.security_classifier import PhoneMessageClassification


class OpenAISecurityClassifier:
    def __init__(self, *, api_key: str, model: str) -> None:
        self._client, self._model = OpenAI(api_key=api_key), model

    def classify(self, message: str) -> PhoneMessageClassification:
        response = self._client.responses.create(model=self._model, instructions="Analyze this stored phone/SMS message for scams, fraud, phishing, coercion, or malicious cyber-security intent. Return only the schema. Do not analyze general conversation.", input=message, text={"format": {"type": "json_schema", "name": "phone_message_security", "strict": True, "schema": PhoneMessageClassification.model_json_schema()}})
        return PhoneMessageClassification.model_validate_json(response.output_text)
