from django.contrib.auth import login
import logging
import re
import secrets
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.throttling import ScopedRateThrottle
from .models import AdminAuditLog, InstructorApplication, User
from .serializers import InstructorApplicationCreateSerializer
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import StudentRegistrationForm
from .serializers import (
    AdminLoginSerializer,
    InstructorLoginSerializer,
    StudentLoginSerializer,
    StudentRegistrationSerializer,
)


def register(request):
    if request.user.is_authenticated:
        return redirect("course_list")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("course_list")
    else:
        form = StudentRegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


class StudentRegistrationAPIView(APIView):
    """Create a student account and issue its authentication token."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = StudentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                },
            },
            status=201,
        )

class StudentLoginAPIView(APIView):
    """Issue a DRF token for valid student credentials."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = StudentLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                },
            },
            status=status.HTTP_200_OK,
        )


class InstructorLoginAPIView(APIView):
    """Issue a DRF token for valid instructor credentials."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = InstructorLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "is_staff": user.is_staff,
                },
            },
            status=status.HTTP_200_OK,
        )


class AdminLoginAPIView(APIView):
    """Issue a token only to an active Django superuser."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": "ADMIN",
                    "is_staff": user.is_staff,
                },
            },
            status=status.HTTP_200_OK,
        )


logger = logging.getLogger(__name__)
OTP_LIFETIME_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_WAIT_SECONDS = 60
OTP_MAX_RESENDS = 3


def _send_instructor_otp(application, otp):
    sent = send_mail(
        subject="Verify your Tech Haven instructor application",
        message=(
            f"Hello {application.user.username},\n\n"
            f"Your Tech Haven instructor application verification code is {otp}.\n"
            f"This code expires in {OTP_LIFETIME_MINUTES} minutes.\n\n"
            "After email verification, your application will be reviewed by a Tech Haven administrator. "
            "Email verification alone does not grant instructor privileges.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.user.email],
        fail_silently=False,
    )
    if sent != 1:
        raise RuntimeError("The verification email could not be sent.")


def _application_payload(application):
    user = application.user
    return {
        "id": application.id,
        "username": user.username,
        "email": user.email,
        "qualification": application.qualification,
        "awarding_institution": application.awarding_institution,
        "experience_summary": application.experience_summary,
        "cv_filename": Path(application.cv.name).name if application.cv else "",
        "has_qualification_document": bool(application.qualification_document),
        "qualification_filename": Path(application.qualification_document.name).name if application.qualification_document else "",
        "status": application.status,
        "created_at": application.created_at.isoformat(),
        "email_verified_at": application.email_verified_at.isoformat() if application.email_verified_at else None,
    }


class IsPlatformSuperuser(BasePermission):
    """Instructor accounts may have is_staff=True; only Django superusers can review applicants."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_superuser
        )


class InstructorApplicationCreateAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "instructor_application"

    def post(self, request):
        serializer = InstructorApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attrs = dict(serializer.validated_data)
        password = attrs.pop("password")
        attrs.pop("password_confirm")
        cv = attrs.pop("cv")
        qualification_document = attrs.pop("qualification_document", None)
        application = None
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=attrs.pop("username"),
                    email=attrs.pop("email"),
                    password=password,
                    role=User.Roles.STUDENT,
                    is_active=False,
                    is_staff=False,
                )
                application = InstructorApplication.objects.create(
                    user=user,
                    cv=cv,
                    qualification_document=qualification_document,
                    status=InstructorApplication.Status.PENDING_EMAIL,
                    **attrs,
                )
                otp = f"{secrets.randbelow(1_000_000):06d}"
                application.otp_hash = make_password(otp)
                application.otp_expires_at = timezone.now() + timedelta(minutes=OTP_LIFETIME_MINUTES)
                application.otp_last_sent_at = timezone.now()
                application.otp_attempts = 0
                application.save(update_fields=["otp_hash", "otp_expires_at", "otp_last_sent_at", "otp_attempts", "updated_at"])
                _send_instructor_otp(application, otp)
        except Exception:
            if application is not None:
                for field_name in ("cv", "qualification_document"):
                    file_field = getattr(application, field_name, None)
                    if file_field and file_field.name:
                        try:
                            file_field.storage.delete(file_field.name)
                        except Exception:
                            logger.exception("Could not clean up an instructor application upload.")
            logger.exception("Unable to create/send OTP for instructor application.")
            return Response(
                {"detail": "We could not start your application or send the verification email. Check the email service and try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "detail": "Application received. Enter the one-time code sent to your email to complete Phase 1.",
                "application_id": application.id,
                "email": application.user.email,
                "status": application.status,
                "otp_expires_in_seconds": OTP_LIFETIME_MINUTES * 60,
            },
            status=status.HTTP_201_CREATED,
        )


class InstructorApplicationVerifyOTPAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "instructor_otp_verify"

    def post(self, request):
        application_id = request.data.get("application_id")
        otp = str(request.data.get("otp", "")).strip()
        if not str(application_id or "").isdigit() or not re.fullmatch(r"\d{6}", otp):
            return Response({"detail": "Enter the application reference and the six-digit code."}, status=status.HTTP_400_BAD_REQUEST)
        application = get_object_or_404(InstructorApplication, pk=int(application_id))
        if application.status != InstructorApplication.Status.PENDING_EMAIL:
            return Response({"detail": "This application is no longer awaiting email verification."}, status=status.HTTP_400_BAD_REQUEST)
        if application.otp_attempts >= OTP_MAX_ATTEMPTS:
            return Response({"detail": "Too many incorrect codes. Request a new code or contact support."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if not application.otp_expires_at or timezone.now() >= application.otp_expires_at:
            return Response({"detail": "This code has expired. Request a new verification code."}, status=status.HTTP_400_BAD_REQUEST)
        if not check_password(otp, application.otp_hash):
            application.otp_attempts += 1
            application.save(update_fields=["otp_attempts", "updated_at"])
            remaining = max(0, OTP_MAX_ATTEMPTS - application.otp_attempts)
            return Response({"detail": f"That code is not valid. {remaining} attempt(s) remaining."}, status=status.HTTP_400_BAD_REQUEST)
        now = timezone.now()
        application.status = InstructorApplication.Status.PENDING_REVIEW
        application.email_verified_at = now
        application.otp_hash = ""
        application.otp_expires_at = None
        # Keep the user inactive until an administrator approves the application.
        # This also blocks legacy Django session login routes, not just the React API.
        application.save(update_fields=["status", "email_verified_at", "otp_hash", "otp_expires_at", "updated_at"])
        return Response({
            "detail": "Phase 1 complete: email verified. Your account remains inactive until a superuser completes Phase 2 and approves your instructor application.",
            "application_id": application.id,
            "status": application.status,
        }, status=status.HTTP_200_OK)


class InstructorApplicationResendOTPAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "instructor_otp_resend"

    def post(self, request):
        application_id = request.data.get("application_id")
        if not str(application_id or "").isdigit():
            return Response({"detail": "Enter a valid application reference."}, status=status.HTTP_400_BAD_REQUEST)
        application = get_object_or_404(InstructorApplication, pk=int(application_id))
        if application.status != InstructorApplication.Status.PENDING_EMAIL:
            return Response({"detail": "This application is not awaiting email verification."}, status=status.HTTP_400_BAD_REQUEST)
        now = timezone.now()
        if application.otp_last_sent_at and now < application.otp_last_sent_at + timedelta(seconds=OTP_RESEND_WAIT_SECONDS):
            return Response({"detail": "Please wait at least 60 seconds before requesting another code."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if application.otp_resend_count >= OTP_MAX_RESENDS:
            return Response({"detail": "The resend limit has been reached for this application. Contact support for assistance."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        otp = f"{secrets.randbelow(1_000_000):06d}"
        try:
            _send_instructor_otp(application, otp)
        except Exception:
            logger.exception("Unable to resend instructor application OTP.")
            return Response({"detail": "We could not send a new code. Please try again later."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        application.otp_hash = make_password(otp)
        application.otp_expires_at = now + timedelta(minutes=OTP_LIFETIME_MINUTES)
        application.otp_last_sent_at = now
        application.otp_attempts = 0
        application.otp_resend_count += 1
        application.save(update_fields=["otp_hash", "otp_expires_at", "otp_last_sent_at", "otp_attempts", "otp_resend_count", "updated_at"])
        return Response({"detail": "A new verification code has been sent."}, status=status.HTTP_200_OK)


class AdminInstructorApplicationListAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPlatformSuperuser]

    def get(self, request):
        applications = InstructorApplication.objects.filter(
            status=InstructorApplication.Status.PENDING_REVIEW
        ).select_related("user")
        items = [_application_payload(item) for item in applications]
        return Response({"count": len(items), "results": items}, status=status.HTTP_200_OK)


class AdminInstructorApplicationReviewAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPlatformSuperuser]

    def post(self, request, application_id):
        application = get_object_or_404(
            InstructorApplication.objects.select_related("user"),
            pk=application_id,
        )
        if application.status != InstructorApplication.Status.PENDING_REVIEW or not application.email_verified_at:
            return Response({"detail": "Only email-verified applications awaiting review can be approved or rejected."}, status=status.HTTP_400_BAD_REQUEST)
        decision = str(request.data.get("decision", "")).lower()
        notes = str(request.data.get("admin_notes", "")).strip()
        if decision not in {"approve", "reject"}:
            return Response({"detail": "Decision must be approve or reject."}, status=status.HTTP_400_BAD_REQUEST)
        if len(notes) > 3000:
            return Response({"detail": "Review notes must be 3000 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)
        now = timezone.now()
        user = application.user
        application.reviewed_by = request.user
        application.reviewed_at = now
        application.admin_notes = notes
        if decision == "approve":
            application.status = InstructorApplication.Status.APPROVED
            user.role = User.Roles.INSTRUCTOR
            user.is_staff = True
            user.is_active = True
            message = "Your Tech Haven instructor application has been approved. You can now sign in as an instructor."
            subject = "Your Tech Haven instructor application is approved"
        else:
            application.status = InstructorApplication.Status.REJECTED
            user.is_active = False
            user.is_staff = False
            message = "Your Tech Haven instructor application was not approved at this time."
            if notes:
                message += f" Administrator notes: {notes}"
            subject = "Update on your Tech Haven instructor application"
        with transaction.atomic():
            user.save(update_fields=["role", "is_staff", "is_active"])
            application.save(update_fields=["status", "reviewed_by", "reviewed_at", "admin_notes", "updated_at"])
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        except Exception:
            logger.exception("Application decision saved, but applicant notification email failed.")
        return Response({"detail": f"Application {application.status.lower().replace('_', ' ')}.", "application": _application_payload(application)}, status=status.HTTP_200_OK)


class AdminInstructorApplicationDocumentAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPlatformSuperuser]

    def get(self, request, application_id, document_type):
        application = get_object_or_404(InstructorApplication, pk=application_id)
        fields = {
            "cv": application.cv,
            "qualification": application.qualification_document,
        }
        if document_type not in fields:
            return Response({"detail": "Unknown document type."}, status=status.HTTP_404_NOT_FOUND)
        field = fields[document_type]
        if not field or not field.name:
            return Response({"detail": "This document was not supplied."}, status=status.HTTP_404_NOT_FOUND)
        try:
            handle = field.open("rb")
        except (FileNotFoundError, OSError):
            return Response({"detail": "The uploaded file is unavailable. Check configured persistent/private media storage."}, status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(handle, as_attachment=True, filename=Path(field.name).name, content_type="application/octet-stream")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

class AdminAccountListAPIView(APIView):
    """Search and paginate accounts for platform superusers only."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPlatformSuperuser]

    def get(self, request):
        from django.db.models import Q

        query = str(request.query_params.get("q", "")).strip()[:120]
        role = str(request.query_params.get("role", "ALL")).upper()
        state_filter = str(request.query_params.get("status", "ALL")).upper()

        users = User.objects.all().order_by("username", "id")
        if query:
            users = users.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
        if role == "ADMIN":
            users = users.filter(is_superuser=True)
        elif role == "INSTRUCTOR":
            users = users.filter(is_superuser=False, role=User.Roles.INSTRUCTOR)
        elif role == "STUDENT":
            users = users.filter(is_superuser=False, role=User.Roles.STUDENT)
        elif role != "ALL":
            return Response({"detail": "Choose a valid account role filter."}, status=status.HTTP_400_BAD_REQUEST)

        if state_filter == "ACTIVE":
            users = users.filter(is_active=True)
        elif state_filter == "INACTIVE":
            users = users.filter(is_active=False)
        elif state_filter != "ALL":
            return Response({"detail": "Choose a valid account status filter."}, status=status.HTTP_400_BAD_REQUEST)

        total = users.count()
        try:
            page = max(1, int(request.query_params.get("page", "1")))
            page_size = int(request.query_params.get("page_size", "25"))
        except (TypeError, ValueError):
            return Response({"detail": "Page and page_size must be positive integers."}, status=status.HTTP_400_BAD_REQUEST)
        page_size = min(50, max(1, page_size))
        pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, pages)
        start = (page - 1) * page_size

        results = [_admin_account_payload(user) for user in users[start:start + page_size]]
        all_users = User.objects.all()
        summary = {
            "total": all_users.count(),
            "students": all_users.filter(is_superuser=False, role=User.Roles.STUDENT).count(),
            "instructors": all_users.filter(is_superuser=False, role=User.Roles.INSTRUCTOR).count(),
            "admins": all_users.filter(is_superuser=True).count(),
            "inactive": all_users.filter(is_active=False).count(),
        }
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "summary": summary,
            "results": results,
        }, status=status.HTTP_200_OK)


class AdminAccountDetailAPIView(APIView):
    """Activate/deactivate ordinary accounts and record every state change."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPlatformSuperuser]

    def patch(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        if target.is_superuser:
            return Response({"detail": "Administrator accounts cannot be changed from this screen."}, status=status.HTTP_403_FORBIDDEN)

        if set(request.data.keys()) != {"is_active", "reason"} or not isinstance(request.data.get("is_active"), bool):
            return Response({"detail": "Send is_active as a true or false value and provide a reason."}, status=status.HTTP_400_BAD_REQUEST)
        reason = request.data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return Response({"detail": "A reason is required for every account access change."}, status=status.HTTP_400_BAD_REQUEST)
        reason = reason.strip()
        if len(reason) > 500:
            return Response({"detail": "Reason must be 500 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)

        requested_active = request.data["is_active"]
        if target.is_active != requested_active:
            with transaction.atomic():
                target.is_active = requested_active
                target.save(update_fields=["is_active"])
                if not requested_active:
                    Token.objects.filter(user=target).delete()
                AdminAuditLog.objects.create(
                    actor=request.user,
                    actor_username=request.user.get_username(),
                    target=target,
                    target_username=target.get_username(),
                    action=AdminAuditLog.Actions.ACTIVATED if requested_active else AdminAuditLog.Actions.DEACTIVATED,
                    reason=reason,
                )

        label = "activated" if requested_active else "deactivated"
        return Response({
            "detail": f"Account {target.username} is {label}.",
            "account": _admin_account_payload(target),
        }, status=status.HTTP_200_OK)

def _admin_account_payload(user):
    role = "ADMIN" if user.is_superuser else user.role
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": role,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }

class AdminOverviewAPIView(APIView):
    """Aggregate live platform statistics for administrators."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPlatformSuperuser]

    def get(self, request):
        from academy.models import Certificate, Course, Enrollment, Submission
        from .models import AdminAuditLog

        users = User.objects.all()
        applications = InstructorApplication.objects.all()
        pending_applications = applications.filter(status=InstructorApplication.Status.PENDING_REVIEW).count()
        pending_submissions = Submission.objects.filter(status__in=["submitted", "pending", "pending_review"]).count()
        summary = {
            "total_accounts": users.count(),
            "active_accounts": users.filter(is_active=True).count(),
            "inactive_accounts": users.filter(is_active=False).count(),
            "students": users.filter(is_superuser=False, role=User.Roles.STUDENT).count(),
            "instructors": users.filter(is_superuser=False, role=User.Roles.INSTRUCTOR).count(),
            "administrators": users.filter(is_superuser=True).count(),
            "courses": Course.objects.count(),
            "enrollments": Enrollment.objects.count(),
            "submissions": Submission.objects.count(),
            "pending_submissions": pending_submissions,
            "graded_submissions": Submission.objects.filter(status="graded").count(),
            "certificates_issued": Certificate.objects.count(),
            "instructor_applications_pending_review": pending_applications,
            "instructor_applications_pending_email": applications.filter(status=InstructorApplication.Status.PENDING_EMAIL).count(),
            "instructor_applications_approved": applications.filter(status=InstructorApplication.Status.APPROVED).count(),
            "instructor_applications_rejected": applications.filter(status=InstructorApplication.Status.REJECTED).count(),
        }
        recent_accounts = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": "ADMIN" if user.is_superuser else user.role,
                "is_active": user.is_active,
                "date_joined": user.date_joined.isoformat() if user.date_joined else None,
            }
            for user in users.order_by("-date_joined", "-id")[:8]
        ]
        recent_audit_events = [_admin_audit_payload(event) for event in AdminAuditLog.objects.select_related("actor", "target")[:8]]
        return Response({
            "summary": summary,
            "recent_accounts": recent_accounts,
            "recent_audit_events": recent_audit_events,
        }, status=status.HTTP_200_OK)


class AdminAuditLogListAPIView(APIView):
    """Filter and paginate audit events; available only to active superusers."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPlatformSuperuser]

    def get(self, request):
        from django.db.models import Q
        from .models import AdminAuditLog

        query = str(request.query_params.get("q", "")).strip()[:120]
        action = str(request.query_params.get("action", "ALL")).upper()
        events = AdminAuditLog.objects.select_related("actor", "target").all()
        if action in (AdminAuditLog.Actions.ACTIVATED, AdminAuditLog.Actions.DEACTIVATED):
            events = events.filter(action=action)
        elif action != "ALL":
            return Response({"detail": "Choose a valid audit action filter."}, status=status.HTTP_400_BAD_REQUEST)
        if query:
            events = events.filter(
                Q(actor_username__icontains=query)
                | Q(target_username__icontains=query)
                | Q(reason__icontains=query)
            )
        count = events.count()
        try:
            page = max(1, int(request.query_params.get("page", "1")))
            page_size = min(50, max(1, int(request.query_params.get("page_size", "25"))))
        except (TypeError, ValueError):
            return Response({"detail": "Page and page_size must be positive integers."}, status=status.HTTP_400_BAD_REQUEST)
        pages = max(1, (count + page_size - 1) // page_size)
        page = min(page, pages)
        start = (page - 1) * page_size
        return Response({
            "count": count,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "summary": {
                "all": AdminAuditLog.objects.count(),
                "activations": AdminAuditLog.objects.filter(action=AdminAuditLog.Actions.ACTIVATED).count(),
                "deactivations": AdminAuditLog.objects.filter(action=AdminAuditLog.Actions.DEACTIVATED).count(),
            },
            "results": [_admin_audit_payload(event) for event in events[start:start + page_size]],
        }, status=status.HTTP_200_OK)


def _admin_audit_payload(event):
    return {
        "id": event.id,
        "actor_username": event.actor_username,
        "target_username": event.target_username,
        "action": event.action,
        "reason": event.reason,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
