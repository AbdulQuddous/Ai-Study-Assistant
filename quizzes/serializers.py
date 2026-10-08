from rest_framework import serializers

from .models import Choice, Question, Quiz, QuizAttempt


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = [
            "id",
            "order",
            "text",
        ]


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "order",
            "text",
            "explanation",
            "difficulty",
            "choices",
        ]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    document_title = serializers.CharField(
        source="document.title",
        read_only=True,
    )

    class Meta:
        model = Quiz
        fields = [
            "id",
            "document",
            "document_title",
            "title",
            "description",
            "question_count",
            "model_used",
            "is_active",
            "created_at",
            "updated_at",
            "questions",
        ]
        read_only_fields = [
            "id",
            "document_title",
            "question_count",
            "model_used",
            "is_active",
            "created_at",
            "updated_at",
            "questions",
        ]


class QuizAttemptSerializer(serializers.ModelSerializer):
    percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "quiz",
            "score",
            "total_questions",
            "percentage",
            "answers",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "score",
            "total_questions",
            "percentage",
            "answers",
            "created_at",
        ]