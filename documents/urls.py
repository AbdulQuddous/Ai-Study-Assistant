from django.urls import path

from .views import document_list, document_upload


urlpatterns = [
    path(
        "",
        document_list,
        name="document_list",
    ),

    path(
        "upload/",
        document_upload,
        name="document_upload",
    ),
]