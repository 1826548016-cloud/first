from django.contrib import admin

from .models import StudySession, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "created_time", "deadline")
    list_filter = ("status",)
    search_fields = ("title", "description", "remark")
    ordering = ("-created_time",)


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "minutes", "session_date", "created_time")
    list_filter = ("category", "session_date")
    search_fields = ("remark",)
    ordering = ("-session_date", "-created_time")
