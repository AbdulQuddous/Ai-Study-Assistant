import logging

from django.db import DatabaseError, transaction

from quizzes.exceptions import QuizPersistenceError
from quizzes.models import Choice, Question, Quiz

logger = logging.getLogger(__name__)


class QuizPersister:
    @transaction.atomic
    def save(self, document, user, quiz_data, model_used=""):
        """Persist a validated quiz payload and return the Quiz.

        Deactivates the user's previous active quizzes for this document inside
        the same transaction, so a failure leaves the old quiz active.
        """
        questions = quiz_data.get("questions") if isinstance(quiz_data, dict) else None
        if not questions or not isinstance(questions, list):
            raise QuizPersistenceError("No questions to save.")

        try:
            with transaction.atomic():
                Quiz.objects.filter(document=document, user=user, is_active=True).update(
                    is_active=False
                )
                quiz = Quiz.objects.create(
                    document=document,
                    user=user,
                    title=quiz_data["title"][:200],
                    description=quiz_data.get("description", ""),
                    question_count=len(questions),
                    model_used=model_used or "",
                )
                for q_order, q in enumerate(questions, start=1):
                    question = Question.objects.create(
                        quiz=quiz,
                        order=q_order,
                        text=q["text"],
                        explanation=q.get("explanation", ""),
                        correct_choice_index=q["correct_choice_index"],
                        difficulty=q.get("difficulty", ""),
                        source_chunk_ids=[],
                    )
                    for c_order, text in enumerate(q["choices"]):
                        Choice.objects.create(question=question, order=c_order, text=text)
        except (DatabaseError, KeyError, TypeError) as exc:
            logger.warning("Quiz persistence failed: %s", exc)
            raise QuizPersistenceError(f"Could not save quiz: {exc}") from exc
        return quiz
