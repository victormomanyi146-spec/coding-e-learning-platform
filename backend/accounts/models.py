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
from django.core.exceptions import ImproperlyConfigured as _ImproperlyConfigured
from django.core.files.storage import FileSystemStorage as _FileSystemStorage
from django.core.files.storage import Storage as _Storage
from django.db import models as _models
from django.utils.deconstruct import deconstructible as _deconstructible
import os as _os


@_deconstructible
class PrivateInstructorDocumentStorage(_Storage):
    # Local development uses filesystem storage. Deployments with DEBUG=False
    # default to S3-compatible storage and fail closed if required settings are absent.

    def __init__(self):
        debug_env = (
            _os.environ.get("DJANGO_DEBUG", "True").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        default_mode = "filesystem" if debug_env else "s3"
        mode = _os.environ.get(
            "INSTRUCTOR_DOCUMENT_STORAGE", default_mode
        ).strip().lower()

        if mode in {"filesystem", "file", "local"}:
            if not debug_env:
                raise _ImproperlyConfigured(
                    "Filesystem storage for instructor documents is allowed only "
                    "when DJANGO_DEBUG=True. Configure private S3-compatible storage."
                )

            location = _os.environ.get(
                "INSTRUCTOR_PRIVATE_UPLOAD_ROOT",
                str(_settings.BASE_DIR / "private_uploads"),
            )
            self._backend = _FileSystemStorage(
                location=location,
                base_url="/private-instructor-documents-not-served/",
            )
            return

        if mode not in {"s3", "s3-compatible"}:
            raise _ImproperlyConfigured(
                "INSTRUCTOR_DOCUMENT_STORAGE must be 'filesystem' or 's3'."
            )

        bucket = _os.environ.get("INSTRUCTOR_DOCUMENTS_S3_BUCKET", "").strip()
        region = _os.environ.get("INSTRUCTOR_DOCUMENTS_S3_REGION", "").strip()

        if not bucket or not region:
            raise _ImproperlyConfigured(
                "INSTRUCTOR_DOCUMENTS_S3_BUCKET and INSTRUCTOR_DOCUMENTS_S3_REGION "
                "are required for private instructor-document storage."
            )

        access_key = _os.environ.get(
            "INSTRUCTOR_DOCUMENTS_S3_ACCESS_KEY", ""
        ).strip()
        secret_key = _os.environ.get(
            "INSTRUCTOR_DOCUMENTS_S3_SECRET_KEY", ""
        ).strip()
        session_token = _os.environ.get(
            "INSTRUCTOR_DOCUMENTS_S3_SESSION_TOKEN", ""
        ).strip()

        if bool(access_key) != bool(secret_key):
            raise _ImproperlyConfigured(
                "Set both INSTRUCTOR_DOCUMENTS_S3_ACCESS_KEY and "
                "INSTRUCTOR_DOCUMENTS_S3_SECRET_KEY, or neither."
            )

        if session_token and not (access_key and secret_key):
            raise _ImproperlyConfigured(
                "INSTRUCTOR_DOCUMENTS_S3_SESSION_TOKEN requires both access-key variables."
            )

        try:
            expiry = int(
                _os.environ.get(
                    "INSTRUCTOR_DOCUMENTS_S3_QUERYSTRING_EXPIRE", "300"
                )
            )
        except ValueError as exc:
            raise _ImproperlyConfigured(
                "INSTRUCTOR_DOCUMENTS_S3_QUERYSTRING_EXPIRE must be a positive integer."
            ) from exc

        if expiry < 1:
            raise _ImproperlyConfigured(
                "INSTRUCTOR_DOCUMENTS_S3_QUERYSTRING_EXPIRE must be a positive integer."
            )

        try:
            from storages.backends.s3 import S3Storage
        except ImportError as exc:
            raise _ImproperlyConfigured(
                "S3 storage requires django-storages with its S3 dependencies. "
                "Install the project requirements."
            ) from exc

        options = {
            "bucket_name": bucket,
            "region_name": region,
            "default_acl": None,
            "querystring_auth": True,
            "querystring_expire": expiry,
            "file_overwrite": False,
            "object_parameters": {"CacheControl": "private, no-store"},
        }

        endpoint = _os.environ.get(
            "INSTRUCTOR_DOCUMENTS_S3_ENDPOINT_URL", ""
        ).strip()
        prefix = _os.environ.get(
            "INSTRUCTOR_DOCUMENTS_S3_PREFIX", ""
        ).strip().strip("/")

        if endpoint:
            options["endpoint_url"] = endpoint
        if prefix:
            options["location"] = prefix
        if access_key and secret_key:
            options["access_key"] = access_key
            options["secret_key"] = secret_key
        if session_token:
            options["security_token"] = session_token

        self._backend = S3Storage(**options)

    def _open(self, name, mode="rb"):
        return self._backend._open(name, mode)

    def _save(self, name, content):
        return self._backend._save(name, content)

    def delete(self, name):
        return self._backend.delete(name)

    def exists(self, name):
        return self._backend.exists(name)

    def listdir(self, path):
        return self._backend.listdir(path)

    def size(self, name):
        return self._backend.size(name)

    def url(self, name):
        return self._backend.url(name)

    def path(self, name):
        return self._backend.path(name)

    def get_accessed_time(self, name):
        return self._backend.get_accessed_time(name)

    def get_created_time(self, name):
        return self._backend.get_created_time(name)

    def get_modified_time(self, name):
        return self._backend.get_modified_time(name)

    def get_valid_name(self, name):
        return self._backend.get_valid_name(name)

    def get_available_name(self, name, max_length=None):
        return self._backend.get_available_name(name, max_length=max_length)

    def generate_filename(self, filename):
        return self._backend.generate_filename(filename)

    def get_alternative_name(self, file_root, file_ext):
        return self._backend.get_alternative_name(file_root, file_ext)


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
