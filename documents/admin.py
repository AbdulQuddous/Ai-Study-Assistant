from django.contrib import admin

from .models import Document, DocumentChunk


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


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "chunk_index",
        "created_at",
    )

    search_fields = (
        "content",
        "document__title",
    )

    list_filter = (
        "document",
        "created_at",
    )