from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import QuizError
from .models import Quiz, QuizAttempt
from .serializers import (
    QuizAttemptSerializer,
    QuizAttemptSubmissionSerializer,
    QuizSerializer,
)
from .services.quiz_scorer import QuizScorer

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

class QuizAttemptAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        quiz = (
            Quiz.objects
            .filter(
                pk=pk,
                user=request.user,
                is_active=True,
            )
            .first()
        )

        if quiz is None:
            return Response(
                {
                    "detail": "Quiz not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = QuizAttemptSubmissionSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        submitted_answers = serializer.validated_data["answers"]

        try:
            submitted_answers = {
                int(question_id): choice_index
                for question_id, choice_index
                in submitted_answers.items()
            }
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": "Invalid question ID."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = QuizScorer().score(
                quiz,
                submitted_answers,
            )
        except QuizError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user=request.user,
            score=result["score"],
            total_questions=result["total_questions"],
            answers=result["answers"],
        )

        response_serializer = QuizAttemptSerializer(
            attempt
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )