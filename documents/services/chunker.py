def chunk_text(text, chunk_size=1000, overlap=200):
    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0."
        )

    if overlap < 0:
        raise ValueError(
            "overlap cannot be negative."
        )

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size."
        )

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(
            start + chunk_size,
            text_length,
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start += chunk_size - overlap

    return chunks