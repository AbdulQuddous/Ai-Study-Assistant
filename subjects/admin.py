from django.contrib import admin

from .models import Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "user",
        "created_at",
    )

    search_fields = (
        "name",
        "description",
        "user__username",
    )

    list_filter = (
        "created_at",
    )