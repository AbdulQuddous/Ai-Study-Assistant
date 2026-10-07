from django.contrib import admin

from .models import Choice, Question, Quiz, QuizAttempt


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "document", "question_count", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "user__username")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "quiz", "difficulty", "correct_choice_index")
    list_filter = ("difficulty",)
    inlines = [ChoiceInline]


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "question", "order")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("__str__", "quiz", "user", "created_at")
    list_filter = ("created_at",)
