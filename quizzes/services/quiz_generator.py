import json
import logging
import re

from django.conf import settings

from quizzes.exceptions import QuizGenerationError
from quizzes.prompts.quiz_generation import RETRY_REMINDER, build_quiz_prompt

logger = logging.getLogger(__name__)

# --- Adapt these to the existing RAG models (check before use) -------------
CHUNK_RELATED_NAME = "chunks"      # Document -> chunks reverse accessor
CHUNK_ORDER_FIELD = "chunk_index"
CHUNK_TEXT_FIELD = "content"
CHUNK_EMBEDDING_FIELD = "embedding"
# ---------------------------------------------------------------------------

CHUNK_SEPARATOR = "\n\n---\n\n"
DIFFICULTIES = {"easy", "medium", "hard"}


def validate_quiz_payload(data, num_questions):
    """Validate a parsed quiz payload. Raises QuizGenerationError on failure."""

    def fail(reason):
        raise QuizGenerationError(f"Invalid quiz payload: {reason}")

    if not isinstance(data, dict):
        fail("top level is not an object")
    for key in ("title", "description", "questions"):
        if key not in data:
            fail(f"missing key '{key}'")
    title = data["title"]
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        fail("title must be a non-empty string up to 200 chars")
    if not isinstance(data["description"], str):
        fail("description must be a string")
    questions = data["questions"]
    max_allowed = min(num_questions, settings.QUIZ_MAX_QUESTION_COUNT)
    if not isinstance(questions, list) or not 1 <= len(questions) <= max_allowed:
        fail(f"questions must be a list of 1..{max_allowed} items")

    for i, q in enumerate(questions, start=1):
        if not isinstance(q, dict):
            fail(f"question {i} is not an object")
        if not isinstance(q.get("text"), str) or not q["text"].strip():
            fail(f"question {i}: text must be a non-empty string")
        if not isinstance(q.get("explanation"), str):
            fail(f"question {i}: explanation must be a string")
        if q.get("difficulty") not in DIFFICULTIES:
            fail(f"question {i}: difficulty must be easy, medium or hard")
        choices = q.get("choices")
        if (
            not isinstance(choices, list)
            or len(choices) != settings.QUIZ_CHOICES_PER_QUESTION
            or not all(isinstance(c, str) and c.strip() for c in choices)
        ):
            fail(
                f"question {i}: choices must be "
                f"{settings.QUIZ_CHOICES_PER_QUESTION} non-empty strings"
            )
        if len(set(choices)) != len(choices):
            fail(f"question {i}: duplicate choices")
        idx = q.get("correct_choice_index")
        if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx <= 3:
            fail(f"question {i}: correct_choice_index must be an int 0-3")


def extract_json(text):
    """Extract and parse the JSON object from a raw LLM response."""
    text = (text or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise QuizGenerationError(
            f"Response was not valid JSON: {exc}"
        ) from exc


class QuizGenerator:
    def __init__(self, llm=None):
        if llm is None:
            from ai_assistant.services.llm import LLMService

            llm = LLMService()
        self.llm = llm

    @property
    def model_used(self):
        """Name of the model used, for storing on Quiz.model_used."""
        return getattr(self.llm, "model_name", "") or getattr(
            settings, "GEMINI_MODEL", ""
        )

    def _load_chunks(self, document):
        manager = getattr(document, CHUNK_RELATED_NAME)
        return list(manager.order_by(CHUNK_ORDER_FIELD))

    def _build_context(self, chunks, num_questions):
        desired = min(len(chunks), num_questions * 2)

        # Evenly spaced indices across the whole document, first and
        # last always included. Formula: round(i * (n-1) / (desired-1)).
        if desired <= 1:
            selected = [chunks[0]]
        else:
            selected = [
                chunks[round(i * (len(chunks) - 1) / (desired - 1))]
                for i in range(desired)
            ]

        per_chunk_cap = max(1, settings.QUIZ_MAX_CONTEXT_CHARS // desired)
        texts = [
            str(getattr(c, CHUNK_TEXT_FIELD))[:per_chunk_cap]
            for c in selected
        ]
        return CHUNK_SEPARATOR.join(texts)

    def _call_llm(self, prompt):
        raw = self.llm.generate(prompt)
        return raw if isinstance(raw, str) else getattr(raw, "text", str(raw))

    def generate(self, document, num_questions=None):
        """Generate a validated quiz payload. Never touches the DB."""
        if num_questions is None:
            num_questions = settings.QUIZ_DEFAULT_QUESTION_COUNT
        num_questions = max(
            1, min(num_questions, settings.QUIZ_MAX_QUESTION_COUNT)
        )

        chunks = self._load_chunks(document)
        if not chunks:
            raise QuizGenerationError("Document has no indexed chunks.")

        context = self._build_context(chunks, num_questions)
        prompt = build_quiz_prompt(
            context=context, num_questions=num_questions
        )

        last_error, last_raw = None, ""
        for attempt in range(2):
            to_send = prompt if attempt == 0 else prompt + RETRY_REMINDER
            try:
                last_raw = self._call_llm(to_send)
            except Exception as exc:  # noqa: BLE001
                # Provider exception types are unknown; wrapped and re-raised.
                logger.warning(
                    "LLM call failed (attempt %s): %s", attempt + 1, exc
                )
                last_error = QuizGenerationError(
                    f"LLM call failed: {exc}"
                )
                continue
            try:
                data = extract_json(last_raw)
                if isinstance(data, dict) and isinstance(
                    data.get("questions"), list
                ):
                    data["questions"] = data["questions"][:num_questions]
                validate_quiz_payload(data, num_questions)
                return data
            except QuizGenerationError as exc:
                logger.warning(
                    "Quiz payload rejected (attempt %s): %s",
                    attempt + 1,
                    exc,
                )
                last_error = exc

        raise QuizGenerationError(
            f"{last_error} | raw response: {last_raw[:500]}"
        )