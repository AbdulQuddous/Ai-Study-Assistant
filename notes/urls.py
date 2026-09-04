from django.urls import path

from .views import note_create, note_detail, note_list


urlpatterns = [
    path("", note_list, name="note_list"),
    path("create/", note_create, name="note_create"),
    path("<int:pk>/", note_detail, name="note_detail"),
]