import os
import httpx
from app.ports.ai_extractor import AIExtractor


class HttpAiClient(AIExtractor):
    """HTTP implementation of the AI extractor"""

    def __init__(
        self,
        api_key: str = os.getenv("PROVIDER_API_KEY", "test-dev-2026"),
        base_url: str = os.getenv("PROVIDER_BASE_URL", "http://localhost:3001"),
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client

    async def extract_intent(self, user_input: str) -> str:
        url = f"{self.base_url}/v1/ai/extract"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        system_prompt = (
            "You are an expert intent extraction assistant for a notification service. "
            "Analyze the user's natural language input and extract notification details. "
            "You must return ONLY a valid JSON object with the following schema:\n"
            '{\n'
            '  "to": "<destination email or phone number>",\n'
            '  "message": "<the body of the notification>",\n'
            '  "type": "<email or sms>"\n'
            '}\n'
            "Strict rules:\n"
            "- 'type' must be strictly 'email' or 'sms'.\n"
            "- Do not wrap the JSON in conversational filler, markdown formatting, or code blocks."
        )
        data = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ]
        }

        if self._client:
            response = await self._client.post(url, headers=headers, json=data, timeout=10.0)
        else:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=data)

        response.raise_for_status()
        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No choices found in the response")
        return choices[0]["message"]["content"]
