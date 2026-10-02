from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from documents.models import Document

from .forms import QAForm
from .services.qa import QAService


@login_required
def document_qa(request, document_id):
    document = get_object_or_404(
        Document,
        id=document_id,
        user=request.user,
    )

    answer = None
    error = None

    if request.method == "POST":
        form = QAForm(request.POST)

        if form.is_valid():
            question = form.cleaned_data["question"]

            if not document.extracted_text.strip():
                error = (
                    "This document does not contain "
                    "extractable text."
                )
            else:
                qa_service = QAService()

                try:
                    answer = qa_service.answer(
                        question=question,
                        study_material=document.extracted_text,
                    )

                except Exception:
                    error = (
                        "Unable to answer the question "
                        "right now. Please try again."
                    )
    else:
        form = QAForm()

    return render(
        request,
        "ai_assistant/document_qa.html",
        {
            "document": document,
            "form": form,
            "answer": answer,
            "error": error,
        },
    )