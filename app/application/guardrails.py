import json
import re
import logging
from typing import Optional
from pydantic import ValidationError
from app.domain.models import NotificationPayload, NotificationType

logger = logging.getLogger("Guardrails")


class GuardrailValidationError(Exception):
    """Exception raised when a guardrail validation fails"""
    pass


class AIRefusalError(GuardrailValidationError):
    """Exception raised when the AI refuses to process the request"""
    pass


class GuardrailsService:
    """Service for sanitizing, repairing and validating LLM responses"""

    REFUSAL_PATTERNS = [
        r"no tengo permitido",
        r"viola las políticas",
        r"refused",
        r"cannot process",
        r"unable to identify",
        r"sensitive information",
        r"can't process",
        r"cannot help",
    ]

    SYNONYMS_MAP = {
        # Recipient synonyms
        "recipient": "to",
        "destination": "to",
        "to": "to",
        # Message synonyms
        "message": "message",
        "body": "message",
        "content": "message",
        "text": "message",
        # Channel / Type synonyms
        "channel": "type",
        "chanel": "type",
        "type": "type",
        "category": "type",
        "method": "type",
    }

    @classmethod
    def process_and_validate(
        cls, raw_content: str, user_input: Optional[str] = None
    ) -> NotificationPayload:
        """
        Main entry point for processing and validating raw LLM content.
        Cleans, repairs and returns a valid NotificationPayload.
        """
        # 1. Check if the AI refused the request
        cls._check_for_refusal(raw_content)

        # 2. Extract JSON block from markdown or conversational text
        json_content = cls._extract_json_block(raw_content)

        # 3. Repair common JSON syntax errors (quotes, missing keys quotes, truncated strings)
        repaired_candidate = cls._repair_json_syntax(json_content)

        # 4. Parse the JSON string into a Python dict
        parsed_payload = cls._parse_json(repaired_candidate, raw_content)

        # 5. Normalize key names using synonyms map
        normalized_payload = cls._normalize_keys(parsed_payload)

        # 6. Rescue missing fields using heuristics and user input
        rescued_payload = cls._rescue_missing_fields(normalized_payload, user_input)

        # 7. Validate with Pydantic domain model
        try:
            return NotificationPayload(**rescued_payload)
        except ValidationError as e:
            raise GuardrailValidationError(f"Pydantic validation error: {e}") from e
        except Exception as e:
            raise GuardrailValidationError(f"Unexpected validation error: {e}") from e

    @classmethod
    def _check_for_refusal(cls, raw_content: str) -> None:
        """Check if the raw content contains a known refusal pattern."""
        lowered = raw_content.lower()
        for pattern in cls.REFUSAL_PATTERNS:
            if re.search(pattern, lowered):
                raise AIRefusalError(f"AI refused request: {raw_content.strip()}")

    @classmethod
    def _extract_json_block(cls, text: str) -> str:
        """Extract JSON substring, handling code blocks or embedded text."""
        # 1. Markdown code blocks (```json { ... } ``` or ``` { ... } ```)
        code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()

        # 2. Embedded JSON in plain text between the first '{' and the last '}'
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1].strip()

        # 3. Truncated JSON starting with '{' but no closing '}'
        if start != -1:
            return text[start:].strip()

        return text.strip()

    @classmethod
    def _repair_json_syntax(cls, text: str) -> str:
        """Repair unquoted keys, single quotes, and truncated JSON blocks."""
        repaired = text.strip()

        # Handle truncated JSON ending with '...' (e.g. {"to": "...", "message": "...", "type": "..." ...)
        if repaired.endswith("..."):
            repaired = repaired[:-3].rstrip().rstrip(",")
            if not repaired.endswith("}"):
                repaired += "}"

        # Fix unquoted keys: {to: "...", message: "..."} -> {"to": "...", "message": "..."}
        repaired = re.sub(r"([{,]\s*)([a-zA-Z_]\w*)\s*:", r'\1"\2":', repaired)

        # Fix single quotes around keys or string values: {'to': '...'} -> {"to": "..."}
        if "'" in repaired and '"' not in repaired:
            repaired = repaired.replace("'", '"')

        return repaired

    @classmethod
    def _parse_json(cls, repaired_text: str, original_raw: str) -> dict:
        """Parse repaired text into dict, with fallback for mixed single quotes."""
        try:
            return json.loads(repaired_text)
        except json.JSONDecodeError:
            try:
                # Fallback: replace any remaining single quotes with double quotes
                fixed_quotes = re.sub(r"\'", '"', repaired_text)
                return json.loads(fixed_quotes)
            except json.JSONDecodeError as err:
                raise GuardrailValidationError(
                    f"Unable to parse repaired JSON: '{repaired_text}'. Raw: '{original_raw}'"
                ) from err

    @classmethod
    def _normalize_keys(cls, data: dict) -> dict:
        """Map synonyms to canonical domain fields (to, message, type)."""
        normalized = {}
        for key, val in data.items():
            canonical_key = cls.SYNONYMS_MAP.get(str(key).lower(), str(key).lower())
            normalized[canonical_key] = val
        return normalized

    @classmethod
    def _rescue_missing_fields(cls, data: dict, user_input: Optional[str] = None) -> dict:
        """Infer and rescue missing 'type' or 'to' fields."""
        # 1. Rescue notification type ('email' vs 'sms')
        if "type" not in data or not data["type"]:
            target = str(data.get("to", ""))
            if "@" in target:
                data["type"] = NotificationType.EMAIL.value
            elif re.search(r"\d", target):
                data["type"] = NotificationType.SMS.value

        # 2. Rescue destination ('to') from user_input if missing in LLM response
        if ("to" not in data or not data["to"]) and user_input:
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", user_input)
            phone_match = re.search(r"\b\d{3}-?\d{3}-?\d{3,4}\b", user_input)
            if email_match:
                data["to"] = email_match.group(0)
                if "type" not in data or not data["type"]:
                    data["type"] = NotificationType.EMAIL.value
            elif phone_match:
                data["to"] = phone_match.group(0)
                if "type" not in data or not data["type"]:
                    data["type"] = NotificationType.SMS.value

        # 3. Ensure 'type' is lowercase
        if "type" in data and isinstance(data["type"], str):
            data["type"] = data["type"].lower()

        return data
