import logging

from quizzes.exceptions import QuizScoringError

logger = logging.getLogger(__name__)


class QuizScorer:
    def score(self, quiz, submitted_answers):
        """Score submitted answers ({question_id: chosen_index}) against the quiz.

        Missing or malformed answers count as wrong (chosen_index = -1).
        Extra keys are ignored. Correctness is always recomputed server-side.
        """
        questions = list(quiz.questions.all())
        if not questions:
            logger.warning("Cannot score quiz %s: no questions", quiz.pk)
            raise QuizScoringError("Quiz has no questions.")

        answers = []
        score = 0
        for question in questions:
            chosen = submitted_answers.get(question.id, -1)
            if isinstance(chosen, bool) or not isinstance(chosen, int) or not 0 <= chosen <= 3:
                chosen = -1
            is_correct = chosen == question.correct_choice_index
            score += int(is_correct)
            answers.append(
                {
                    "question_id": question.id,
                    "chosen_index": chosen,
                    "correct_index": question.correct_choice_index,
                    "is_correct": is_correct,
                }
            )
        return {"score": score, "total_questions": len(questions), "answers": answers}
