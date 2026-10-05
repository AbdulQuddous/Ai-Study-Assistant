from django.conf import settings

from .embeddings import EmbeddingService
from .similarity import cosine_similarity


class DocumentRetriever:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    def retrieve(
        self,
        document,
        query,
        top_k=None,
        similarity_threshold=None,
    ):
        if top_k is None:
            top_k = settings.RAG_TOP_K

        if similarity_threshold is None:
            similarity_threshold = (
                settings.RAG_SIMILARITY_THRESHOLD
            )

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        if not 0 <= similarity_threshold <= 1:
            raise ValueError(
                "similarity_threshold must be between 0 and 1."
            )

        chunks = (
            document.chunks
            .filter(embedding__isnull=False)
            .order_by("chunk_index")
        )

        if not chunks.exists():
            return []

        query_embedding = (
            self.embedding_service.embed_text(query)
        )

        results = []

        for chunk in chunks:
            similarity = cosine_similarity(
                query_embedding,
                chunk.embedding,
            )

            if similarity >= similarity_threshold:
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

        if not results:
            # Fallback: return top-k of everything if nothing passed
            all_results = []
            for chunk in chunks:
                similarity = cosine_similarity(
                    query_embedding,
                    chunk.embedding,
                )
                all_results.append(
                    {"chunk": chunk, "score": similarity}
                )
            all_results.sort(
                key=lambda item: item["score"],
                reverse=True,
            )
            return all_results[:top_k]

        return results[:top_k]