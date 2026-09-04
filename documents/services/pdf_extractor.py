from pypdf import PdfReader


def extract_text_from_pdf(file):

    reader = PdfReader(file)

    extracted_pages = []

    for page in reader.pages:

        text = page.extract_text()

        if text:
            extracted_pages.append(text)

    return "\n\n".join(extracted_pages)