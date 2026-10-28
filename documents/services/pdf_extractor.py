from pypdf import PdfReader
import re


def extract_text_from_pdf(file):
    file.seek(0)
    reader = PdfReader(file)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported. Upload an unencrypted PDF.")
    extracted_pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            extracted_pages.append(text)

    raw = "\n\n".join(extracted_pages)

    # 1. Join words split across lines by a hyphen: "arith-\nmetic" -> "arithmetic"
    raw = re.sub(r"-\n(\w)", r"\1", raw)

    # 2. Replace single line breaks inside a paragraph with a space
    #    (keeps double newlines = real paragraph breaks)
    raw = re.sub(r"(?<!\n)\n(?!\n)", " ", raw)

    # 3. Collapse runs of spaces
    raw = re.sub(r"[ \t]+", " ", raw)

    text = raw.strip()
    if not text:
        raise ValueError("No text could be extracted. Upload a PDF with selectable text.")
    return text
