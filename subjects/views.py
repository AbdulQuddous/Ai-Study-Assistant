from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from .forms import SubjectForm
from .models import Subject


@login_required
def subject_list(request):

    subjects = Subject.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "subjects/subject_list.html",
        {
            "subjects": subjects
        }
    )


@login_required
def subject_create(request):

    if request.method == "POST":

        form = SubjectForm(
            request.POST
        )

        if form.is_valid():

            subject = form.save(
                commit=False
            )

            subject.user = request.user

            subject.save()

            return redirect(
                "subject_list"
            )

    else:

        form = SubjectForm()

    return render(
        request,
        "subjects/subject_form.html",
        {
            "form": form,
            "title": "Create Subject",
        }
    )


@login_required
def subject_detail(request, pk):

    subject = get_object_or_404(
        Subject,
        pk=pk,
        user=request.user
    )

    return render(
        request,
        "subjects/subject_detail.html",
        {
            "subject": subject
        }
    )


@login_required
def subject_update(request, pk):

    subject = get_object_or_404(
        Subject,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":

        form = SubjectForm(
            request.POST,
            instance=subject
        )

        if form.is_valid():

            form.save()

            return redirect(
                "subject_detail",
                pk=subject.pk
            )

    else:

        form = SubjectForm(
            instance=subject
        )

    return render(
        request,
        "subjects/subject_form.html",
        {
            "form": form,
            "title": "Update Subject",
        }
    )


@login_required
def subject_delete(request, pk):

    subject = get_object_or_404(
        Subject,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":

        subject.delete()

        return redirect(
            "subject_list"
        )

    return render(
        request,
        "subjects/subject_confirm_delete.html",
        {
            "subject": subject
        }
    )