from django.contrib import admin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subject",
        "user",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "title",
        "content",
        "subject__name",
        "user__username",
    )

    list_filter = (
        "subject",
        "created_at",
    )