from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Quiz
from .serializers import QuizSerializer


class QuizListAPIView(generics.ListAPIView):
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Quiz.objects
            .filter(
                user=self.request.user,
                is_active=True,
            )
            .select_related("document")
            .prefetch_related(
                "questions__choices",
            )
        )


class QuizDetailAPIView(generics.RetrieveAPIView):
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Quiz.objects
            .filter(
                user=self.request.user,
                is_active=True,
            )
            .select_related("document")
            .prefetch_related(
                "questions__choices",
            )
        )