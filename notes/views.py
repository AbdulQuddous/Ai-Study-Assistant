from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import NoteForm
from .models import Note


@login_required
def note_list(request):
    notes = Note.objects.filter(
        user=request.user
    ).select_related("subject").order_by("-created_at")

    return render(
        request,
        "notes/note_list.html",
        {
            "notes": notes,
        }
    )


@login_required
def note_detail(request, pk):
    note = get_object_or_404(
        Note.objects.select_related("subject"),
        pk=pk,
        user=request.user,
    )

    return render(
        request,
        "notes/note_detail.html",
        {
            "note": note,
        }
    )


@login_required
def note_create(request):

    if request.method == "POST":
        form = NoteForm(request.POST)

        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()

            return redirect("note_list")

    else:
        form = NoteForm()

    return render(
        request,
        "notes/note_form.html",
        {
            "form": form,
            "title": "Create Note",
        }
    )