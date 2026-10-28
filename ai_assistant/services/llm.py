import logging
import time

from django.conf import settings
from google import genai
from google.genai import errors

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured.")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    def generate(self, prompt, max_retries=3):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")
        if max_retries < 1:
            raise ValueError("max_retries must be positive.")
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt,
                )
                answer = response.text
                if not isinstance(answer, str) or not answer.strip():
                    raise RuntimeError("AI service returned an empty response.")
                return answer.strip()
            except errors.APIError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == max_retries - 1:
                    raise RuntimeError("AI service request failed.") from exc
                # Provider payloads can contain private input or credentials.
                logger.warning("AI service temporarily unavailable (status %s).", exc.code)
                time.sleep(2 ** attempt)
            except Exception as exc:
                raise RuntimeError("AI service request failed.") from exc
        raise RuntimeError("AI service request failed.")
