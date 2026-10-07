import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from documents.models import Document

from .exceptions import QuizError
from .models import Quiz, QuizAttempt
from .services.quiz_generator import QuizGenerator
from .services.quiz_persister import QuizPersister
from .services.quiz_scorer import QuizScorer

logger = logging.getLogger(__name__)


@login_required
@require_POST
def quiz_generate(request, pk):
    """Generate and persist a quiz for one of the user's documents."""
    document = get_object_or_404(Document, pk=pk, user=request.user)
    try:
        generator = QuizGenerator()
        quiz_data = generator.generate(document)
        quiz = QuizPersister().save(
            document, request.user, quiz_data, model_used=generator.model_used
        )
    except QuizError as exc:
        logger.warning("Quiz generation failed for document %s: %s", pk, exc)
        messages.error(request, "Could not generate quiz. Please try again.")
        return redirect("documents:document_detail", pk=document.pk)
    messages.success(request, "Quiz generated.")
    return redirect("quizzes:quiz_detail", pk=quiz.pk)


@login_required
def quiz_list(request):
    """List the user's active quizzes with their last attempt score."""
    last = QuizAttempt.objects.filter(quiz=OuterRef("pk")).order_by("-created_at")
    quizzes = (
        Quiz.objects.filter(user=request.user, is_active=True)
        .select_related("document")
        .annotate(
            last_score=Subquery(last.values("score")[:1]),
            last_total=Subquery(last.values("total_questions")[:1]),
        )
    )
    return render(request, "quizzes/quiz_list.html", {"quizzes": quizzes})


@login_required
def quiz_detail(request, pk):
    """Show quiz metadata and past attempts."""
    quiz = get_object_or_404(
        Quiz.objects.select_related("document"), pk=pk, user=request.user, is_active=True
    )
    attempts = quiz.attempts.filter(user=request.user)
    return render(request, "quizzes/quiz_detail.html", {"quiz": quiz, "attempts": attempts})


@login_required
def quiz_take(request, pk):
    """Render the quiz (GET) or score the submitted answers (POST)."""
    quiz = get_object_or_404(Quiz, pk=pk, user=request.user, is_active=True)
    questions = quiz.questions.prefetch_related("choices")

    if request.method == "POST":
        submitted = {}
        for question in questions:
            try:
                chosen = int(request.POST.get(f"q_{question.id}"))
            except (TypeError, ValueError):
                chosen = -1
            submitted[question.id] = chosen if 0 <= chosen <= 3 else -1
        try:
            result = QuizScorer().score(quiz, submitted)
        except QuizError as exc:
            logger.warning("Scoring failed for quiz %s: %s", pk, exc)
            messages.error(request, "Could not score your answers. Please try again.")
            return redirect("quizzes:quiz_take", pk=quiz.pk)
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user=request.user,
            score=result["score"],
            total_questions=result["total_questions"],
            answers=result["answers"],
        )
        return redirect("quizzes:quiz_result", pk=attempt.pk)

    return render(request, "quizzes/quiz_take.html", {"quiz": quiz, "questions": questions})


@login_required
def quiz_result(request, pk):
    """Show an attempt's score and per-question review."""
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz"), pk=pk, user=request.user
    )
    by_id = {a["question_id"]: a for a in attempt.answers}
    review = []
    for question in attempt.quiz.questions.prefetch_related("choices"):
        ans = by_id.get(question.id, {})
        chosen = ans.get("chosen_index", -1)
        review.append(
            {
                "question": question,
                "chosen_index": chosen,
                "is_correct": ans.get("is_correct", False),
                "choices": [
                    {
                        "text": c.text,
                        "is_correct": c.order == question.correct_choice_index,
                        "is_chosen": c.order == chosen,
                    }
                    for c in question.choices.all()
                ],
            }
        )
    return render(
        request, "quizzes/quiz_result.html", {"attempt": attempt, "quiz": attempt.quiz, "review": review}
    )
