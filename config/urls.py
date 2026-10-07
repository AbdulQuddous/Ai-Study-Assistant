# config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required      # ← ADD
from django.shortcuts import render                            # ← ADD
from django.urls import include, path


@login_required                                                # ← ADD this block
def dashboard(request):                                        # ← ADD
    return render(request, "dashboard/dashboard.html")         # ← ADD


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard, name="dashboard"),                     # ← ADD
    path("accounts/", include("accounts.urls")),
    path("subjects/", include("subjects.urls")),
    path("notes/", include("notes.urls")),
    path("documents/", include("documents.urls")),
    path("quizzes/", include("quizzes.urls")),
    path("ai/", include("ai_assistant.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )