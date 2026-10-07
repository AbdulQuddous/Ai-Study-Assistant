from django.urls import path

from .views import document_qa

app_name = "ai_assistant"
urlpatterns = [
    path(
        "documents/<int:document_id>/qa/",
        document_qa,
        name="document_qa",
    ),
]