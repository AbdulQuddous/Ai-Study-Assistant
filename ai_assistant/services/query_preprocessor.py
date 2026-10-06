import re


def preprocess_query(query):
    """
    Normalize a user query before embedding and retrieval.

    - Strips leading/trailing whitespace
    - Collapses runs of whitespace (spaces, tabs, newlines) into single spaces
    - Raises ValueError on empty/whitespace-only input
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    query = query.strip()
    query = re.sub(r"\s+", " ", query)

    return query