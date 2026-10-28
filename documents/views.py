from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from .services.processor import process_document
from .forms import DocumentForm
from .models import Document
from .services.pdf_extractor import extract_text_from_pdf
from ai_assistant.services.summarizer import Summarizer
from quizzes.models import Quiz


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
        {"documents": documents},
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
            document = form.save(commit=False)
            document.user = request.user

            try:
                document.extracted_text = extract_text_from_pdf(document.file)
                process_document(document)
            except ValueError:
                form.add_error(None, "Unable to process this PDF. Use an unencrypted PDF with selectable text and try again.")
            except Exception:
                form.add_error(None, "Unable to process this PDF right now. Please try again.")
            else:
                return redirect("documents:document_list")

    else:
        form = DocumentForm(user=request.user)

    return render(
        request,
        "documents/document_form.html",
        {
            "form": form,
            "title": "Upload PDF",
        },
    )


@login_required
def document_detail(request, pk):
    document = get_object_or_404(
        Document.objects.select_related("subject"),
        pk=pk,
        user=request.user,
    )

    quizzes = (
        Quiz.objects
        .filter(user=request.user, document=document, is_active=True)
        .order_by("-created_at")
    )

    return render(
        request,
        "documents/document_detail.html",
        {
            "document": document,
            "document_quizzes": quizzes,
        },
    )


@login_required
def document_delete(request, pk):
    document = get_object_or_404(
        Document,
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":
        document.delete()
        return redirect("documents:document_list")

    return render(
        request,
        "documents/document_confirm_delete.html",
        {"document": document},
    )


@login_required
def document_summarize(request, pk):
    document = get_object_or_404(
        Document,
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":
        if not document.extracted_text.strip():
            return render(
                request,
                "documents/document_detail.html",
                {
                    "document": document,
                    "summary_error": (
                        "This document does not contain "
                        "extractable text."
                    ),
                },
            )

        try:
            summarizer = Summarizer()
            summary = summarizer.summarize(
                document.extracted_text
            )
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("AI returned an empty summary.")

            document.ai_summary = summary

            document.save(
                update_fields=[
                    "ai_summary",
                    "updated_at",
                ]
            )

        except Exception:
            return render(
                request,
                "documents/document_detail.html",
                {
                    "document": document,
                    "summary_error": (
                        "Unable to generate the summary "
                        "right now. Please try again."
                    ),
                },
            )

    return redirect(
        "documents:document_detail",
        pk=document.pk,
    )


@login_required
def document_file(request, pk):
    document = get_object_or_404(Document, pk=pk, user=request.user)
    try:
        response = FileResponse(document.file.open("rb"), content_type="application/pdf")
    except (FileNotFoundError, ValueError):
        raise Http404("PDF file is unavailable.")
    response["Cache-Control"] = "private, no-store"
    return response
