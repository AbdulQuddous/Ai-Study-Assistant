from django.contrib.auth.models import User
from django.db import models

from documents.models import Document


class ChatMessage(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    question = models.TextField()
    answer = models.TextField()

    sources = models.JSONField(
        default=list,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.document.title}"