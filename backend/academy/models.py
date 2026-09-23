from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(blank=True, unique=True)
    description = models.TextField()
    instructor = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    level = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Module(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules",
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "order",
        ]

        unique_together = (
            "course",
            "order",
        )

    def __str__(self):
        return (
            f"{self.course.title} - "
            f"{self.title}"
        )


class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
    )

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="lessons",
        null=True,
        blank=True,
    )

    title = models.CharField(
        max_length=200,
    )

    content = models.TextField()

    order = models.PositiveIntegerField(
        default=1,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "order",
        ]

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Activity(models.Model):

    ACTIVITY_TYPES = [
        ("reading", "Reading"),
        ("coding", "Coding Exercise"),
        ("quiz", "Quiz"),
        ("assignment", "Assignment"),
        ("lab", "Lab"),
    ]

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="activities",
    )

    title = models.CharField(
        max_length=200,
    )

    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES,
    )

    instructions = models.TextField()

    order = models.PositiveIntegerField(
        default=1,
    )

    max_score = models.PositiveIntegerField(
        default=100,
    )

    is_required = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"


class Submission(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    code = models.TextField()

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    status = models.CharField(
        max_length=20,
        default="submitted",
    )

    score = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    feedback = models.TextField(
        blank=True,
    )

    def __str__(self):
        return f"{self.student.username} - {self.activity.title}"


class ActivityCompletion(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_completions",
    )

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="completions",
    )

    completed_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        unique_together = (
            "student",
            "activity",
        )

    def __str__(self):
        return (
            f"{self.student} - "
            f"{self.activity.title} - Completed"
        )


class Enrollment(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    enrolled_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment",
            )
        ]

        ordering = [
            "-enrolled_at",
        ]

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"