from .llm import LLMService
from ..prompts.qa import build_qa_prompt


class QAService:
    def __init__(self):
        self.llm = LLMService()

    def answer(self, question, study_material):
        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")

        if not study_material or not study_material.strip():
            raise ValueError(
                "Study material cannot be empty."
            )

        prompt = build_qa_prompt(
            question=question,
            study_material=study_material,
        )

        return self.llm.generate(prompt)