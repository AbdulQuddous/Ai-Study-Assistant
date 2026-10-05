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
        similarity_threshold=0.25,
    ):
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        if top_k <= 0:
            raise ValueError("top_k must be greater than 0.")

        if not 0 <= similarity_threshold <= 1:
            raise ValueError(
                "similarity_threshold must be between 0 and 1."
            )

        chunks = (
            document.chunks
            .filter(embedding__isnull=False)
            .order_by("chunk_index")
        )

        total = chunks.count()
        print(
            f"[RETRIEVER] doc={document.pk} "
            f"query={query!r} chunks_with_embedding={total}"
        )

        if not chunks.exists():
            print("[RETRIEVER] no chunks with embeddings -> returning []")
            return []

        query_embedding = self.embedding_service.embed_text(query)
        print(
            f"[RETRIEVER] query_embedding dim={len(query_embedding)} "
            f"first5={query_embedding[:5]}"
        )
        print(f"[RETRIEVER] threshold={similarity_threshold}")

        results = []

        for chunk in chunks:
            if not chunk.embedding:
                continue

            if len(chunk.embedding) != len(query_embedding):
                print(
                    f"[RETRIEVER] chunk={chunk.chunk_index} "
                    f"dim mismatch ({len(chunk.embedding)} "
                    f"vs {len(query_embedding)}), skipping"
                )
                continue

            similarity = cosine_similarity(
                query_embedding,
                chunk.embedding,
            )

            print(
                f"[RETRIEVER] chunk={chunk.chunk_index} "
                f"score={similarity:.4f}"
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

        filtered = [
            r for r in results
            if r["score"] >= similarity_threshold
        ]

        print(
            f"[RETRIEVER] threshold={similarity_threshold} "
            f"passed={len(filtered)} / {len(results)}"
        )

        if not filtered and results:
            print(
                "[RETRIEVER] threshold filtered everything, "
                "returning top-k as fallback"
            )
            return results[:top_k]

        return filtered[:top_k]