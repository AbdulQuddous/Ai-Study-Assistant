from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "subject",
        "user",
        "created_at",
    )

    search_fields = (
        "title",
        "extracted_text",
        "subject__name",
        "user__username",
    )

    list_filter = (
        "subject",
        "created_at",
    )