from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import NoteForm


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