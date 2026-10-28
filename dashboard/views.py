from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from documents.models import Document
from notes.models import Note
from quizzes.models import Quiz, QuizAttempt
from subjects.models import Subject


@login_required
def dashboard(request):
    subjects = Subject.objects.filter(user=request.user)
    notes = Note.objects.filter(user=request.user)
    documents = Document.objects.filter(user=request.user)
    quizzes = Quiz.objects.filter(user=request.user, is_active=True)
    attempts = QuizAttempt.objects.filter(user=request.user)
    return render(request, "dashboard/dashboard.html", {
        "subject_count": subjects.count(),
        "note_count": notes.count(),
        "document_count": documents.count(),
        "quiz_count": quizzes.count(),
        "attempt_count": attempts.count(),
        "recent_documents": documents.only("title").order_by("-created_at", "-pk")[:5],
        "recent_notes": notes.only("title").order_by("-created_at", "-pk")[:5],
        "recent_quizzes": quizzes.order_by("-created_at", "-pk")[:5],
        "recent_attempts": attempts.select_related("quiz").order_by("-created_at", "-pk")[:5],
    })
