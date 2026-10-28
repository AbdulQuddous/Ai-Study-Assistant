from django.urls import path

from .api_views import (
    QuizAttemptAPIView,
    QuizDetailAPIView,
    QuizListAPIView,
)

app_name = "quiz_api"

urlpatterns = [
    path(
        "quizzes/",
        QuizListAPIView.as_view(),
        name="quiz-list",
    ),
    path(
        "quizzes/<int:pk>/",
        QuizDetailAPIView.as_view(),
        name="quiz-detail",
    ),
    path(
        "quizzes/<int:pk>/attempt/",
        QuizAttemptAPIView.as_view(),
        name="quiz-attempt",
    ),
]