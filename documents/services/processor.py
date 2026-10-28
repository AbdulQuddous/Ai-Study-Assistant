from django.db import transaction

from ai_assistant.services.embeddings import EmbeddingService
from ai_assistant.services.similarity import validate_embedding_batch

from ..models import Document, DocumentChunk
from .chunker import chunk_text
from .text_cleaner import clean_text


def process_document(document):
    cleaned_text = clean_text(
        document.extracted_text
    )

    chunks = chunk_text(
        cleaned_text,
        chunk_size=500,
        overlap=100,
    )

    if not chunks:
        raise ValueError("Document does not contain extractable text.")

    embedding_service = EmbeddingService()

    embeddings = embedding_service.embed_texts(
        chunks
    )
    validate_embedding_batch(embeddings, len(chunks))

    # External model work finishes before touching existing persisted content.
    with transaction.atomic():
        if document.pk:
            Document.objects.select_for_update().get(pk=document.pk)
        document.extracted_text = cleaned_text
        if document.pk:
            document.save(update_fields=["extracted_text", "updated_at"])
        else:
            document.save()
        document.chunks.all().delete()
        DocumentChunk.objects.bulk_create(
            [
                DocumentChunk(
                    document=document,
                    chunk_index=index,
                    content=content,
                    embedding=embedding,
                )
                for index, (content, embedding)
                in enumerate(zip(chunks, embeddings))
            ]
        )

    return chunks
