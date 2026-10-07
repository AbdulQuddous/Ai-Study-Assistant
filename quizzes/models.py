from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Quiz(models.Model):
    document = models.ForeignKey(
        "documents.Document", on_delete=models.CASCADE, related_name="quizzes"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    question_count = models.PositiveIntegerField()
    model_used = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["document", "is_active"]),
        ]

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField()
    text = models.TextField()
    explanation = models.TextField(blank=True)
    correct_choice_index = models.PositiveSmallIntegerField()
    difficulty = models.CharField(
        max_length=10,
        choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")],
        blank=True,
    )
    source_chunk_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]
        unique_together = ("quiz", "order")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(correct_choice_index__gte=0)
                & models.Q(correct_choice_index__lte=3),
                name="question_correct_choice_index_0_to_3",
            ),
        ]

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"


class Choice(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="choices"
    )
    order = models.PositiveSmallIntegerField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]
        unique_together = ("question", "order")

    def __str__(self):
        return f"{self.order}: {self.text[:40]}"


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    score = models.PositiveSmallIntegerField()
    total_questions = models.PositiveSmallIntegerField()
    answers = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["quiz"]),
        ]

    def __str__(self):
        return f"{self.user.get_username()} — {self.score}/{self.total_questions}"

    @property
    def percentage(self):
        if not self.total_questions:
            return 0
        return round(100 * self.score / self.total_questions)
