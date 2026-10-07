from django.urls import path
from quizzes import views as quiz_views
from .views import (
    document_delete,
    document_detail,
    document_list,
    document_summarize,
    document_upload,
)
app_name = "documents" 

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
    path(
        "<int:pk>/generate-quiz/",
        quiz_views.quiz_generate,
        name="document_generate_quiz",
    ),
]