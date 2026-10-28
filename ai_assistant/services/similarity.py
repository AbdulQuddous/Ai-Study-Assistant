import math


def validate_embedding_batch(embeddings, expected_count):
    if not isinstance(embeddings, list) or len(embeddings) != expected_count:
        raise ValueError("Embedding count does not match the chunk count.")
    dimension = None
    for vector in embeddings:
        if not isinstance(vector, list) or not vector:
            raise ValueError("Embedding vectors must be non-empty lists.")
        if dimension is None:
            dimension = len(vector)
        if len(vector) != dimension or any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) for value in vector
        ):
            raise ValueError("Embedding vectors must have consistent dimensions and finite numbers.")


def cosine_similarity(vector_a, vector_b):
    if not vector_a or not vector_b:
        return 0.0

    if len(vector_a) != len(vector_b):
        raise ValueError(
            "Vectors must have the same dimensions."
        )

    validate_embedding_batch([vector_a, vector_b], 2)

    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (
        magnitude_a * magnitude_b
    )
