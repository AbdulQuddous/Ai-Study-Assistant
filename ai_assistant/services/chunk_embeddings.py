from documents.models import DocumentChunk

from .embeddings import EmbeddingService


class ChunkEmbeddingService:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    def generate_for_chunk(self, chunk):
        if not chunk.content or not chunk.content.strip():
            raise ValueError(
                "Cannot generate embedding for empty chunk."
            )

        embedding = self.embedding_service.embed_text(
            chunk.content
        )

        chunk.embedding = embedding
        chunk.save(
            update_fields=["embedding"]
        )

        return embedding

    def generate_for_document(self, document):
        chunks = document.chunks.all().order_by(
            "chunk_index"
        )

        if not chunks.exists():
            return 0

        texts = [
            chunk.content
            for chunk in chunks
        ]

        embeddings = self.embedding_service.embed_texts(
            texts
        )

        for chunk, embedding in zip(
            chunks,
            embeddings,
        ):
            chunk.embedding = embedding

        DocumentChunk.objects.bulk_update(
            chunks,
            ["embedding"],
        )

        return len(chunks)