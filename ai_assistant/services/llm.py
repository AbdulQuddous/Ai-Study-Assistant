import time

from django.conf import settings
from google import genai
from google.api_core import exceptions as google_exceptions


class LLMService:

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    def generate(self, prompt, max_retries=3):
        last_exc = None

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                return response.text

            except google_exceptions.ResourceExhausted as exc:
                last_exc = exc
                wait = 2 ** attempt
                print(
                    f"[LLM] Rate limited (attempt {attempt + 1}/{max_retries}), "
                    f"waiting {wait}s: {exc}"
                )
                time.sleep(wait)

            except google_exceptions.ServiceUnavailable as exc:
                last_exc = exc
                wait = 2 ** attempt
                print(
                    f"[LLM] Service unavailable (attempt {attempt + 1}/{max_retries}), "
                    f"waiting {wait}s: {exc}"
                )
                time.sleep(wait)

            except Exception as exc:
                print(f"[LLM] Real error: {type(exc).__name__}: {exc}")
                raise RuntimeError(
                    "AI service request failed."
                ) from exc

        print(f"[LLM] Gave up after {max_retries} retries: {last_exc}")
        raise RuntimeError(
            "AI service request failed after retries."
        ) from last_exc