from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(text, chunk_size=500, overlap=100):
    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")

    if overlap < 0:
        raise ValueError("overlap cannot be negative.")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=[
            "\n\n",   # paragraph
            "\n",     # line
            ". ",     # sentence
            " ",      # word
            "",       # character (last resort)
        ],
        keep_separator=True,
    )

    pieces = splitter.split_text(text)
    return [p.strip() for p in pieces if p.strip()]