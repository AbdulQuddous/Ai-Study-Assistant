from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from documents.models import Document

from .forms import QAForm
from .models import ChatMessage
from .services.rag import RAGService


@login_required
def document_qa(request, document_id):
    document = get_object_or_404(
        Document,
        id=document_id,
        user=request.user,
    )

    answer = None
    sources = []
    error = None

    if request.method == "POST":
        form = QAForm(request.POST)

        if form.is_valid():
            question = form.cleaned_data["question"]

            rag_service = RAGService()

            try:
                result = rag_service.answer(
                    document=document,
                    question=question,
                )

                answer = result["answer"]
                sources = result.get("sources", [])

                ChatMessage.objects.create(
                    user=request.user,
                    document=document,
                    question=question,
                    answer=answer,
                    sources=sources,
                )

            except Exception as e:
                print(
                    f"[VIEW] RAG error: "
                    f"{type(e).__name__}: {e}"
                )
                error = (
                    "Unable to answer the question right now. "
                    "Please try again."
                )
        else:
            error = "Please enter a valid question."
    else:
        form = QAForm()

    chat_messages = (
        ChatMessage.objects
        .filter(
            user=request.user,
            document=document,
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "ai_assistant/document_qa.html",
        {
            "document": document,
            "form": form,
            "answer": answer,
            "error": error,
            "sources": sources,
            "chat_messages": chat_messages,
        },
    )