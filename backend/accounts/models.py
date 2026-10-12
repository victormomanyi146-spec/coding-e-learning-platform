from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Roles(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        INSTRUCTOR = 'INSTRUCTOR', 'Instructor'

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.STUDENT,
    )

    def __str__(self):
        return self.username

# Create your models here.


# Instructor applications use a private, admin-authorized document download endpoint.
from pathlib import Path as _Path
from django.conf import settings as _settings
from django.core.exceptions import ValidationError as _ModelValidationError
from django.core.validators import FileExtensionValidator as _FileExtensionValidator
from django.core.files.storage import FileSystemStorage as _FileSystemStorage
from django.db import models as _models
from django.utils.deconstruct import deconstructible as _deconstructible
import os as _os


@_deconstructible
class PrivateInstructorDocumentStorage(_FileSystemStorage):
    """Keep instructor CVs and qualification records outside publicly served MEDIA_ROOT."""
    def __init__(self):
        location = _os.environ.get(
            "INSTRUCTOR_PRIVATE_UPLOAD_ROOT",
            str(_settings.BASE_DIR / "private_uploads"),
        )
        super().__init__(location=location, base_url="/private-instructor-documents-not-served/")


private_instructor_document_storage = PrivateInstructorDocumentStorage()


def validate_instructor_upload_size(upload):
    max_bytes = 10 * 1024 * 1024
    if upload.size > max_bytes:
        raise _ModelValidationError("Each uploaded document must be 10 MB or smaller.")


def instructor_cv_upload_path(instance, filename):
    return f"private/instructor-applications/{instance.user_id}/cv/{_Path(filename).name}"


def instructor_qualification_upload_path(instance, filename):
    return f"private/instructor-applications/{instance.user_id}/qualification/{_Path(filename).name}"


class InstructorApplication(_models.Model):
    class Status(_models.TextChoices):
        PENDING_EMAIL = "PENDING_EMAIL", "Awaiting email verification"
        PENDING_REVIEW = "PENDING_REVIEW", "Awaiting administrator review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user = _models.OneToOneField(
        _settings.AUTH_USER_MODEL,
        on_delete=_models.CASCADE,
        related_name="instructor_application",
    )
    qualification = _models.CharField(max_length=200)
    awarding_institution = _models.CharField(max_length=200)
    experience_summary = _models.TextField(max_length=3000)
    cv = _models.FileField(
        upload_to=instructor_cv_upload_path,
        storage=private_instructor_document_storage,
        validators=[_FileExtensionValidator(["pdf", "doc", "docx"]), validate_instructor_upload_size],
    )
    qualification_document = _models.FileField(
        upload_to=instructor_qualification_upload_path,
        storage=private_instructor_document_storage,
        validators=[_FileExtensionValidator(["pdf", "doc", "docx", "png", "jpg", "jpeg"]), validate_instructor_upload_size],
        blank=True,
    )
    status = _models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_EMAIL, db_index=True)
    otp_hash = _models.CharField(max_length=128, blank=True)
    otp_expires_at = _models.DateTimeField(null=True, blank=True)
    otp_last_sent_at = _models.DateTimeField(null=True, blank=True)
    otp_attempts = _models.PositiveSmallIntegerField(default=0)
    otp_resend_count = _models.PositiveSmallIntegerField(default=0)
    email_verified_at = _models.DateTimeField(null=True, blank=True)
    reviewed_by = _models.ForeignKey(
        _settings.AUTH_USER_MODEL,
        on_delete=_models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_instructor_applications",
    )
    reviewed_at = _models.DateTimeField(null=True, blank=True)
    admin_notes = _models.TextField(max_length=3000, blank=True)
    created_at = _models.DateTimeField(auto_now_add=True)
    updated_at = _models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Instructor application: {self.user.username} ({self.status})"

class AdminAuditLog(models.Model):
    """Immutable history for account access changes made through admin tools."""

    class Actions(models.TextChoices):
        ACTIVATED = "ACTIVATED", "Account activated"
        DEACTIVATED = "DEACTIVATED", "Account deactivated"

    actor = models.ForeignKey(
        _settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_account_audit_events",
    )
    actor_username = models.CharField(max_length=150)
    target = models.ForeignKey(
        _settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account_access_audit_events",
    )
    target_username = models.CharField(max_length=150)
    action = models.CharField(max_length=20, choices=Actions.choices, db_index=True)
    reason = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["action", "created_at"], name="acct_audit_action_dt_idx"),
        ]

    def __str__(self):
        return f"{self.actor_username}: {self.action} {self.target_username}"
