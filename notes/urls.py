from django.urls import path

from .views import note_create


urlpatterns = [
    path("create/", note_create, name="note_create"),
]