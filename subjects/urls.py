from django.urls import path

from .views import subject_create
from .views import subject_delete
from .views import subject_detail
from .views import subject_list
from .views import subject_update


urlpatterns = [

    path(
        "",
        subject_list,
        name="subject_list"
    ),

    path(
        "create/",
        subject_create,
        name="subject_create"
    ),

    path(
        "<int:pk>/",
        subject_detail,
        name="subject_detail"
    ),

    path(
        "<int:pk>/edit/",
        subject_update,
        name="subject_update"
    ),

    path(
        "<int:pk>/delete/",
        subject_delete,
        name="subject_delete"
    ),
]