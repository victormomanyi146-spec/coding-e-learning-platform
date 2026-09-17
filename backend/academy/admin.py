from django.contrib import admin

from .models import (
    Activity,
    ActivityCompletion,
    Course,
    Lesson,
    Module,
    Submission,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "instructor",
        "level",
        "duration",
        "created_at",
    )
    search_fields = ("title", "instructor")
    list_filter = ("level",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "order",
        "created_at",
    )
    search_fields = ("title", "course__title")
    list_filter = ("course",)
    ordering = ("course", "order")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "module",
        "order",
        "created_at",
    )
    search_fields = (
        "title",
        "course__title",
        "module__title",
    )
    list_filter = ("course", "module")
    ordering = ("course", "module", "order")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "lesson",
        "activity_type",
        "order",
        "max_score",
        "is_required",
        "created_at",
    )
    search_fields = ("title", "lesson__title")
    list_filter = ("activity_type", "is_required")
    ordering = ("lesson", "order")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "activity",
        "status",
        "score",
        "submitted_at",
    )
    search_fields = (
        "student__username",
        "activity__title",
    )
    list_filter = ("status",)
    ordering = ("-submitted_at",)
    readonly_fields = ("submitted_at",)


@admin.register(ActivityCompletion)
class ActivityCompletionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "activity",
        "completed_at",
    )
    search_fields = (
        "student__username",
        "activity__title",
    )
    list_filter = ("activity__lesson__course",)
    ordering = ("-completed_at",)
    readonly_fields = ("completed_at",)
