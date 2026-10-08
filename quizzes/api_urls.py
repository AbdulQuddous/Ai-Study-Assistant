from django.urls import path

from .api_views import (
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
]