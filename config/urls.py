# config/urls.py
from django.contrib import admin
from dashboard.views import dashboard
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard, name="dashboard"),
    path("dashboard/", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("subjects/", include("subjects.urls")),
    path("notes/", include("notes.urls")),
    path("documents/", include("documents.urls")),
    path("quizzes/", include("quizzes.urls")),
    path("ai/", include("ai_assistant.urls")),
    path("api/",include("quizzes.api_urls")),
]
