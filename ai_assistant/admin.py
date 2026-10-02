from django.contrib import admin

from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "document",
        "created_at",
    )

    search_fields = (
        "question",
        "answer",
        "user__username",
        "document__title",
    )

    list_filter = (
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )