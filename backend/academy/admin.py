from django.contrib import admin

from .models import (
    Activity,
    ActivityCompletion,
    Course,
    Enrollment,
    Lesson,
    Module,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizChoice,
    QuizQuestion,
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
    search_fields = (
        "title",
        "instructor",
    )
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
    search_fields = (
        "title",
        "course__title",
    )
    list_filter = ("course",)
    ordering = (
        "course",
        "order",
    )


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
    list_filter = (
        "course",
        "module",
    )
    ordering = (
        "course",
        "module",
        "order",
    )


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
    search_fields = (
        "title",
        "lesson__title",
    )
    list_filter = (
        "activity_type",
        "is_required",
    )
    ordering = (
        "lesson",
        "order",
    )


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
    list_filter = (
        "activity__lesson__course",
    )
    ordering = ("-completed_at",)
    readonly_fields = ("completed_at",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course",
        "enrolled_at",
    )
    search_fields = (
        "student__username",
        "student__email",
        "course__title",
    )
    list_filter = (
        "course",
        "enrolled_at",
    )
    ordering = ("-enrolled_at",)
    readonly_fields = ("enrolled_at",)


# ============================================================
# QUIZ MANAGEMENT
# ============================================================


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1
    fields = (
        "question_text",
        "order",
        "points",
        "is_active",
    )
    ordering = (
        "order",
        "id",
    )


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "quiz_title",
        "course",
        "lesson",
        "passing_score",
        "question_count",
        "created_at",
    )

    search_fields = (
        "activity__title",
        "activity__lesson__title",
        "activity__lesson__course__title",
    )

    list_filter = (
        "passing_score",
        "activity__lesson__course",
    )

    readonly_fields = (
        "created_at",
    )

    inlines = (
        QuizQuestionInline,
    )

    ordering = (
        "activity__lesson__course",
        "activity__lesson",
        "activity__title",
    )

    @admin.display(
        description="Quiz"
    )
    def quiz_title(self, obj):
        return obj.activity.title

    @admin.display(
        description="Course"
    )
    def course(self, obj):
        return obj.activity.lesson.course.title

    @admin.display(
        description="Lesson"
    )
    def lesson(self, obj):
        return obj.activity.lesson.title

    @admin.display(
        description="Questions"
    )
    def question_count(self, obj):
        return obj.questions.count()


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 1
    fields = (
        "choice_text",
        "is_correct",
        "order",
    )
    ordering = (
        "order",
        "id",
    )


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "question_text_short",
        "quiz",
        "course",
        "lesson",
        "order",
        "points",
        "is_active",
    )

    search_fields = (
        "question_text",
        "quiz__activity__title",
        "quiz__activity__lesson__title",
    )

    list_filter = (
        "is_active",
        "points",
        "quiz__activity__lesson__course",
    )

    ordering = (
        "quiz__activity__lesson",
        "order",
        "id",
    )

    inlines = (
        QuizChoiceInline,
    )

    @admin.display(
        description="Question"
    )
    def question_text_short(self, obj):
        text = obj.question_text
        return (
            text[:80] + "..."
            if len(text) > 80
            else text
        )

    @admin.display(
        description="Course"
    )
    def course(self, obj):
        return obj.quiz.activity.lesson.course.title

    @admin.display(
        description="Lesson"
    )
    def lesson(self, obj):
        return obj.quiz.activity.lesson.title


@admin.register(QuizChoice)
class QuizChoiceAdmin(admin.ModelAdmin):
    list_display = (
        "choice_text",
        "question",
        "quiz",
        "is_correct",
        "order",
    )

    search_fields = (
        "choice_text",
        "question__question_text",
        "question__quiz__activity__title",
    )

    list_filter = (
        "is_correct",
        "question__quiz__activity__lesson__course",
    )

    ordering = (
        "question",
        "order",
        "id",
    )

    @admin.display(
        description="Quiz"
    )
    def quiz(self, obj):
        return obj.question.quiz.activity.title


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "quiz",
        "score",
        "passed",
        "completed_at",
        "created_at",
    )

    search_fields = (
        "student__username",
        "student__email",
        "quiz__activity__title",
        "quiz__activity__lesson__title",
    )

    list_filter = (
        "passed",
        "quiz__activity__lesson__course",
    )

    ordering = (
        "-created_at",
        "-id",
    )

    readonly_fields = (
        "quiz",
        "student",
        "score",
        "passed",
        "completed_at",
        "created_at",
    )


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "attempt",
        "question",
        "selected_choice",
        "is_correct",
        "points_awarded",
    )

    search_fields = (
        "attempt__student__username",
        "question__question_text",
        "selected_choice__choice_text",
    )

    list_filter = (
        "is_correct",
        "question__quiz__activity__lesson__course",
    )

    ordering = (
        "-attempt__created_at",
        "question__order",
    )

    readonly_fields = (
        "attempt",
        "question",
        "selected_choice",
        "is_correct",
        "points_awarded",
    )
