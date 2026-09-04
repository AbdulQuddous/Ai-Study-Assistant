from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import NoteForm
from .models import Note


@login_required
def note_list(request):

    search_query = request.GET.get("q", "").strip()

    notes = Note.objects.filter(
        user=request.user
    ).select_related("subject")

    if search_query:
        notes = notes.filter(
            Q(title__icontains=search_query)
            | Q(content__icontains=search_query)
            | Q(subject__name__icontains=search_query)
        )

    notes = notes.order_by("-created_at")

    paginator = Paginator(notes, 6)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "notes/note_list.html",
        {
            "page_obj": page_obj,
            "search_query": search_query,
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

        form = NoteForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            note = form.save(
                commit=False
            )

            note.user = request.user

            note.save()

            return redirect("note_list")

    else:

        form = NoteForm(
            user=request.user
        )

    return render(
        request,
        "notes/note_form.html",
        {
            "form": form,
            "title": "Create Note",
        }
    )

@login_required
def note_update(request, pk):

    note = get_object_or_404(
        Note,
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":

        form = NoteForm(
            request.POST,
            instance=note,
            user=request.user
        )

        if form.is_valid():

            form.save()

            return redirect(
                "note_detail",
                pk=note.pk
            )

    else:

        form = NoteForm(
            instance=note,
            user=request.user
        )

    return render(
        request,
        "notes/note_form.html",
        {
            "form": form,
            "title": "Update Note",
        }
    )

@login_required
def note_delete(request, pk):
    note = get_object_or_404(
        Note,
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":
        note.delete()

        return redirect("note_list")

    return render(
        request,
        "notes/note_confirm_delete.html",
        {
            "note": note,
        }
    )