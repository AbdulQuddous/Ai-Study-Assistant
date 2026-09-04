from .llm import LLMService
from ..prompts.summary import build_summary_prompt


class Summarizer:
    def __init__(self):
        self.llm = LLMService()

    def summarize(self, text):
        if not text or not text.strip():
            raise ValueError(
                "Cannot summarize empty text."
            )

        prompt = build_summary_prompt(text)

        return self.llm.generate(prompt)