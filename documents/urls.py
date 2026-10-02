from django.urls import path

from .views import (
    document_delete,
    document_detail,
    document_list,
    document_summarize,
    document_upload,
)


urlpatterns = [
    path("", document_list, name="document_list"),

    path(
        "upload/",
        document_upload,
        name="document_upload",
    ),

    path(
        "<int:pk>/",
        document_detail,
        name="document_detail",
    ),

    path(
        "<int:pk>/delete/",
        document_delete,
        name="document_delete",
    ),

    path(
        "<int:pk>/summarize/",
        document_summarize,
        name="document_summarize",
    ),
]