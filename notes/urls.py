from django.urls import path

from .views import (
    note_create,
    note_delete,
    note_detail,
    note_list,
    note_update,
)
app_name = "notes"

urlpatterns = [
    path("", note_list, name="note_list"),

    path("create/", note_create, name="note_create"),

    path("<int:pk>/", note_detail, name="note_detail"),

    path(
        "<int:pk>/edit/",
        note_update,
        name="note_update",
    ),

    path(
        "<int:pk>/delete/",
        note_delete,
        name="note_delete",
    ),
]