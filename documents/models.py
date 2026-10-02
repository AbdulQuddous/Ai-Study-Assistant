from django.contrib.auth.models import User
from django.db import models

from subjects.models import Subject

from .validators import validate_pdf


class Document(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    title = models.CharField(max_length=200)

    file = models.FileField(
        upload_to="documents/",
        validators=[validate_pdf],
    )

    extracted_text = models.TextField(
        blank=True
    )

    ai_summary = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()

    embedding = models.JSONField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"