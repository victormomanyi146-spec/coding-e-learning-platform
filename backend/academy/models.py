import uuid

from django.core.validators import FileExtensionValidator
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


class Quiz(models.Model):

    activity = models.OneToOneField(
        Activity,
        on_delete=models.CASCADE,
        related_name="quiz",
    )

    passing_score = models.PositiveIntegerField(
        default=50,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.activity.title} - Quiz"

class QuizQuestion(models.Model):

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    question_text = models.TextField()

    order = models.PositiveIntegerField(
        default=1,
    )

    points = models.PositiveIntegerField(
        default=1,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            "order",
        ]

        unique_together = (
            "quiz",
            "order",
        )

    def __str__(self):
        return (
            f"{self.quiz.activity.title} - "
            f"Question {self.order}"
        )

class QuizChoice(models.Model):

    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="choices",
    )

    choice_text = models.CharField(
        max_length=500,
    )

    is_correct = models.BooleanField(
        default=False,
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    class Meta:
        ordering = [
            "order",
        ]

        unique_together = (
            "question",
            "order",
        )

    def __str__(self):
        return (
            f"{self.question} - "
            f"Choice {self.order}"
        )

class QuizAttempt(models.Model):

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="attempts",
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )

    score = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    passed = models.BooleanField(
        default=False,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.student.username} - "
            f"{self.quiz.activity.title} - "
            f"Attempt {self.pk}"
        )

class QuizAnswer(models.Model):

    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    selected_choice = models.ForeignKey(
        QuizChoice,
        on_delete=models.CASCADE,
        related_name="selected_answers",
        null=True,
        blank=True,
    )

    is_correct = models.BooleanField(
        default=False,
    )

    points_awarded = models.PositiveIntegerField(
        default=0,
    )

    def __str__(self):
        return (
            f"{self.attempt.student.username} - "
            f"{self.question}"
        )

    class Meta:
        unique_together = (
            "attempt",
            "question",
        )

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

    response_text = models.TextField(
        blank=True,
        help_text="Written response or explanation for assignment/lab submissions.",
    )

    github_url = models.URLField(
        blank=True,
        help_text="Optional GitHub repository or submission URL.",
    )

    attachment = models.FileField(
        upload_to="submissions/",
        blank=True,
        null=True,
        help_text="Optional supporting file for an assignment/lab submission.",
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf",
                    "doc",
                    "docx",
                    "txt",
                    "zip",
                    "py",
                    "ipynb",
                    "png",
                    "jpg",
                    "jpeg",
                ]
            )
        ],
    )

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

class Certificate(models.Model):

    verification_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificates",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="certificates",
    )

    learner_name = models.CharField(
        max_length=255,
    )

    course_title = models.CharField(
        max_length=200,
    )

    average_score = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    issued_at = models.DateTimeField(
        auto_now_add=True,
    )

    is_valid = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_certificate",
            )
        ]

        ordering = [
            "-issued_at",
        ]

    def __str__(self):
        return (
            f"{self.learner_name} - "
            f"{self.course_title} - "
            f"{self.verification_code}"
        )


class Notification(models.Model):

    NOTIFICATION_TYPES = (
        ("graded", "Graded"),
        ("correction", "Needs Correction"),
        ("general", "General"),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default="general",
    )

    title = models.CharField(
        max_length=200,
    )

    message = models.TextField()

    link_url = models.CharField(
        max_length=500,
        blank=True,
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]
        indexes = [
            models.Index(
                fields=["recipient", "is_read"],
                name="notif_recipient_read_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.recipient.username} - "
            f"{self.title}"
        )

