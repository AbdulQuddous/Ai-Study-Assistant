from documents.models import Document

from .embeddings import EmbeddingService
from .similarity import cosine_similarity


class DocumentRetriever:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    def retrieve(
        self,
        document,
        query,
        top_k=5,
    ):
        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        chunks = (
            document.chunks
            .filter(embedding__isnull=False)
            .order_by("chunk_index")
        )

        if not chunks.exists():
            return []

        query_embedding = (
            self.embedding_service.embed_text(
                query
            )
        )

        results = []

        for chunk in chunks:
            similarity = cosine_similarity(
                query_embedding,
                chunk.embedding,
            )

            results.append(
                {
                    "chunk": chunk,
                    "score": similarity,
                }
            )

        results.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return results[:top_k]