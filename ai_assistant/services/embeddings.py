from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        settings.EMBEDDING_MODEL
    )


class EmbeddingService:
    @property
    def model(self):
        return get_embedding_model()

    def embed_text(self, text):
        if not text or not text.strip():
            raise ValueError("Text cannot be empty.")

        vector = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        return vector.tolist()

    def embed_texts(self, texts):
        if not texts:
            return []

        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
        )

        return vectors.tolist()
