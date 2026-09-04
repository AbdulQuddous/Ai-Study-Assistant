from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import DocumentForm
from .models import Document
from .services.pdf_extractor import extract_text_from_pdf


@login_required
def document_list(request):

    documents = (
        Document.objects
        .filter(user=request.user)
        .select_related("subject")
        .order_by("-created_at")
    )

    return render(
        request,
        "documents/document_list.html",
        {
            "documents": documents,
        },
    )


@login_required
def document_upload(request):

    if request.method == "POST":

        form = DocumentForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():

            document = form.save(
                commit=False
            )

            document.user = request.user

            document.extracted_text = (
                extract_text_from_pdf(
                    document.file
                )
            )

            document.save()

            return redirect(
                "document_list"
            )

    else:

        form = DocumentForm(
            user=request.user
        )

    return render(
        request,
        "documents/document_form.html",
        {
            "form": form,
            "title": "Upload PDF",
        },
    )