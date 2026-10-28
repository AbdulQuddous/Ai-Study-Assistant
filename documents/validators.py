from django.core.exceptions import ValidationError


def validate_pdf(file):

    if not file.name.lower().endswith(".pdf"):
        raise ValidationError(
            "Only PDF files are allowed."
        )

    if file.size > 10 * 1024 * 1024:
        raise ValidationError(
            "PDF file size must be 10 MB or less."
        )

    position = file.tell()
    try:
        file.seek(0)
        if not file.read(5) == b"%PDF-":
            raise ValidationError("The uploaded file is not a valid PDF.")
    finally:
        file.seek(position)
