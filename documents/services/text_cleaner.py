import re


def clean_text(text):
    if not text:
        return ""

    # Replace Windows-style line endings
    text = text.replace("\r\n", "\n")

    # Replace remaining carriage returns
    text = text.replace("\r", "\n")

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Reduce excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()