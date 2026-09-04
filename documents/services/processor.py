from django.db import transaction

from ..models import Document, DocumentChunk
from .chunker import chunk_text
from .text_cleaner import clean_text


@transaction.atomic
def process_document(document):
    cleaned_text = clean_text(
        document.extracted_text
    )

    document.extracted_text = cleaned_text
    document.save(
        update_fields=[
            "extracted_text",
            "updated_at",
        ]
    )

    document.chunks.all().delete()

    chunks = chunk_text(
        cleaned_text,
        chunk_size=1000,
        overlap=200,
    )

    DocumentChunk.objects.bulk_create(
        [
            DocumentChunk(
                document=document,
                chunk_index=index,
                content=content,
            )
            for index, content in enumerate(chunks)
        ]
    )

    return chunks