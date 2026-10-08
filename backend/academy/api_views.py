from django.utils import timezone
from django.db import transaction
from django.urls import reverse
import os
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework.parsers import (
    FormParser,
    JSONParser,
    MultiPartParser,
)

from .models import (
    Activity,
    ActivityCompletion,
    Certificate,
    Course,
    Enrollment,
    Notification,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizChoice,
    Submission,
)
from .api_serializers import (
    CertificateAPISerializer,
    CourseDetailAPISerializer,
    CourseListAPISerializer,
    QuizAPISerializer,
    QuizAttemptAPISerializer,
    SubmissionAPISerializer,
)

from .views import (
    _course_progress,
    _is_activity_unlocked,
    _lesson_is_completed,
    _mark_progress,
    _module_progress,
    _notify_submission_review,
)


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "link_url",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields


class NotificationListAPIView(APIView):
    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        notifications = (
            Notification.objects
            .filter(recipient=request.user)
            .order_by("-created_at")
        )

        serializer = NotificationSerializer(
            notifications,
            many=True,
        )

        return Response(
            {
                "count": notifications.count(),
                "unread_count": notifications.filter(
                    is_read=False,
                ).count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UnreadNotificationListAPIView(APIView):
    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        notifications = (
            Notification.objects
            .filter(
                recipient=request.user,
                is_read=False,
            )
            .order_by("-created_at")
        )

        serializer = NotificationSerializer(
            notifications,
            many=True,
        )

        return Response(
            {
                "count": notifications.count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class NotificationReadAPIView(APIView):
    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, notification_id):
        notification = Notification.objects.filter(
            id=notification_id,
            recipient=request.user,
        ).first()

        if notification is None:
            return Response(
                {
                    "detail": "Notification not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not notification.is_read:
            notification.is_read = True
            notification.save(
                update_fields=["is_read"],
            )

        serializer = NotificationSerializer(
            notification,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ============================================================
# COURSE CATALOG API
# ============================================================

class CourseListAPIView(APIView):
    """
    Return the public course catalog.
    """

    permission_classes = []

    def get(self, request):
        courses = (
            Course.objects
            .all()
            .order_by("created_at", "title")
        )

        serializer = CourseListAPISerializer(
            courses,
            many=True,
        )

        return Response(
            {
                "count": courses.count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class CourseDetailAPIView(APIView):
    """
    Return one course with its modules, lessons,
    and activities.
    """

    permission_classes = []

    def get(self, request, slug):
        course = (
            Course.objects
            .prefetch_related(
                "modules__lessons__activities",
            )
            .filter(slug=slug)
            .first()
        )

        if course is None:
            return Response(
                {
                    "detail": "Course not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CourseDetailAPISerializer(
            course,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

# ============================================================
# AUTHENTICATED COURSE ENROLLMENT API
# ============================================================

class CourseEnrollAPIView(APIView):
    """
    Enroll the authenticated student in a course.
    """

    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, slug):
        if getattr(request.user, "role", None) != "STUDENT":
            return Response(
                {
                    "detail": "Only students can enroll in courses.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        course = (
            Course.objects
            .filter(slug=slug)
            .first()
        )

        if course is None:
            return Response(
                {
                    "detail": "Course not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user,
            course=course,
        )

        return Response(
            {
                "detail": (
                    "Enrollment created."
                    if created
                    else "Already enrolled."
                ),
                "created": created,
                "enrollment": {
                    "id": enrollment.id,
                    "student": request.user.username,
                    "course": {
                        "id": course.id,
                        "title": course.title,
                        "slug": course.slug,
                    },
                    "enrolled_at": enrollment.enrolled_at,
                },
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


# ============================================================
# AUTHENTICATED COURSE PROGRESS API
# ============================================================

class CourseProgressAPIView(APIView):
    """
    Return the authenticated student's progress for one course.
    """

    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, slug):
        course = (
            Course.objects
            .prefetch_related(
                "modules__lessons__activities",
            )
            .filter(slug=slug)
            .first()
        )

        if course is None:
            return Response(
                {
                    "detail": "Course not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        enrollment = (
            Enrollment.objects
            .filter(
                student=request.user,
                course=course,
            )
            .first()
        )

        if enrollment is None:
            return Response(
                {
                    "detail": "Enrollment required.",
                    "course": {
                        "id": course.id,
                        "title": course.title,
                        "slug": course.slug,
                    },
                    "is_enrolled": False,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        progress = _course_progress(
            request.user,
            course,
        )

        modules = (
            course.modules
            .all()
            .order_by("order", "id")
        )

        module_results = []

        for module in modules:
            module_progress = _module_progress(
                request.user,
                module,
            )

            lesson_results = []

            for lesson in module.lessons.all().order_by(
                "order",
                "id",
            ):
                lesson_results.append(
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "order": lesson.order,
                        "is_completed": _lesson_is_completed(
                            request.user,
                            lesson,
                        ),
                    }
                )

            module_results.append(
                {
                    "id": module.id,
                    "title": module.title,
                    "order": module.order,
                    "progress_percentage": module_progress[
                        "percentage"
                    ],
                    "lessons_completed": module_progress[
                        "completed_lessons"
                    ],
                    "lessons_total": module_progress[
                        "total_lessons"
                    ],
                    "activities_completed": module_progress[
                        "completed"
                    ],
                    "activities_total": module_progress[
                        "total"
                    ],
                    "lessons": lesson_results,
                }
            )

        course_completed = (
            progress["lessons_total"] > 0
            and progress["lessons_completed"]
            == progress["lessons_total"]
        )

        return Response(
            {
                "course": {
                    "id": course.id,
                    "title": course.title,
                    "slug": course.slug,
                },
                "is_enrolled": True,
                "course_completed": course_completed,
                "progress": {
                    "overall_percentage": progress["percentage"],
                    "lesson_percentage": progress[
                        "lesson_percentage"
                    ],
                    "activity_percentage": progress[
                        "activity_percentage"
                    ],
                    "lessons_completed": progress[
                        "lessons_completed"
                    ],
                    "lessons_total": progress[
                        "lessons_total"
                    ],
                    "activities_completed": progress[
                        "activities_completed"
                    ],
                    "activities_total": progress[
                        "activities_total"
                    ],
                    "average_score": progress[
                        "average_score"
                    ],
                },
                "modules": module_results,
                "recent_assessments": progress[
                    "recent_assessments"
                ],
            },
            status=status.HTTP_200_OK,
        )



# ============================================================
# READING ACTIVITY COMPLETION API
# ============================================================

class ActivityCompleteAPIView(APIView):
    """
    Mark a reading activity complete for the authenticated student.
    """

    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, activity_id):
        if getattr(
            request.user,
            "role",
            None,
        ) != "STUDENT":
            return Response(
                {
                    "detail": (
                        "Only students can complete "
                        "reading activities."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        activity = (
            Activity.objects
            .select_related(
                "lesson",
                "lesson__course",
            )
            .filter(
                id=activity_id,
            )
            .first()
        )

        if activity is None:
            return Response(
                {
                    "detail": "Activity not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if activity.activity_type != "reading":
            return Response(
                {
                    "detail": (
                        "Only reading activities can be "
                        "completed through this endpoint."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        course = activity.lesson.course

        if not Enrollment.objects.filter(
            student=request.user,
            course=course,
        ).exists():
            return Response(
                {
                    "detail": "Enrollment required.",
                    "course": {
                        "id": course.id,
                        "title": course.title,
                        "slug": course.slug,
                    },
                    "is_enrolled": False,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not _is_activity_unlocked(
            request.user,
            activity,
        ):
            return Response(
                {
                    "detail": "This activity is currently locked.",
                    "activity": {
                        "id": activity.id,
                        "title": activity.title,
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        completion, created = (
            ActivityCompletion.objects.get_or_create(
                student=request.user,
                activity=activity,
            )
        )

        progress = _course_progress(
            request.user,
            course,
        )

        return Response(
            {
                "detail": (
                    "Reading activity completed."
                    if created
                    else "Reading activity was already completed."
                ),
                "created": created,
                "activity": {
                    "id": activity.id,
                    "title": activity.title,
                    "is_completed": True,
                },
                "course": {
                    "id": course.id,
                    "title": course.title,
                    "slug": course.slug,
                },
                "progress": {
                    "overall_percentage": progress["percentage"],
                    "lesson_percentage": progress[
                        "lesson_percentage"
                    ],
                    "activity_percentage": progress[
                        "activity_percentage"
                    ],
                    "lessons_completed": progress[
                        "lessons_completed"
                    ],
                    "lessons_total": progress[
                        "lessons_total"
                    ],
                    "activities_completed": progress[
                        "activities_completed"
                    ],
                    "activities_total": progress[
                        "activities_total"
                    ],
                },
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )

# ============================================================
# SUBMISSIONS API
# ============================================================


class SubmissionListCreateAPIView(APIView):
    """
    GET:
        Students see their own submissions.
        Instructors/admins see all submissions.

    POST:
        Students create coding, assignment, or lab submissions.
    """

    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    def get(self, request):

        queryset = (
            Submission.objects
            .select_related(
                "student",
                "activity",
                "activity__lesson",
                "activity__lesson__course",
            )
            .order_by(
                "-submitted_at",
                "-id",
            )
        )

        is_instructor = (
            request.user.is_staff
            or getattr(request.user, "role", None) == "INSTRUCTOR"
        )

        if not is_instructor:
            queryset = queryset.filter(
                student=request.user,
            )

        status_filter = str(
            request.query_params.get(
                "status",
                "all",
            )
        ).strip().lower()

        valid_filters = {
            "all",
            "submitted",
            "pending",
            "graded",
            "correction",
            "error",
        }

        if status_filter not in valid_filters:
            return Response(
                {
                    "detail": "Invalid status filter.",
                    "allowed_statuses": sorted(
                        valid_filters,
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if status_filter == "submitted":
            queryset = queryset.filter(
                status="submitted",
            )

        elif status_filter == "pending":
            queryset = queryset.filter(
                status="submitted",
                score__isnull=True,
            )

        elif status_filter in {
            "graded",
            "correction",
            "error",
        }:
            queryset = queryset.filter(
                status=status_filter,
            )

        serializer = SubmissionAPISerializer(
            queryset,
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "count": queryset.count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):

        if getattr(
            request.user,
            "role",
            None,
        ) != "STUDENT":

            return Response(
                {
                    "detail": (
                        "Only students can create submissions."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        activity_value = request.data.get(
            "activity",
        )

        try:
            activity_id = int(
                activity_value,
            )
        except (
            TypeError,
            ValueError,
        ):
            return Response(
                {
                    "detail": (
                        "A valid activity id is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        activity = (
            Activity.objects
            .select_related(
                "lesson",
                "lesson__course",
            )
            .filter(
                id=activity_id,
            )
            .first()
        )

        if activity is None:
            return Response(
                {
                    "detail": "Activity not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        course = activity.lesson.course

        if not Enrollment.objects.filter(
            student=request.user,
            course=course,
        ).exists():

            return Response(
                {
                    "detail": "Enrollment required.",
                    "course": {
                        "id": course.id,
                        "title": course.title,
                        "slug": course.slug,
                    },
                    "is_enrolled": False,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not _is_activity_unlocked(
            request.user,
            activity,
        ):

            return Response(
                {
                    "detail": (
                        "This activity is currently locked."
                    ),
                    "activity": {
                        "id": activity.id,
                        "title": activity.title,
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if activity.activity_type not in {
            "coding",
            "assignment",
            "lab",
        }:

            return Response(
                {
                    "detail": (
                        "Only coding, assignment, and lab "
                        "activities accept submissions."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = str(
            request.data.get(
                "code",
                "",
            )
            or ""
        ).strip()

        response_text = str(
            request.data.get(
                "response_text",
                "",
            )
            or ""
        ).strip()

        github_url = str(
            request.data.get(
                "github_url",
                "",
            )
            or ""
        ).strip()

        attachment = request.FILES.get(
            "attachment",
        )

        # ----------------------------------------------------
        # CODING
        # ----------------------------------------------------

        if activity.activity_type == "coding":

            if not code:
                return Response(
                    {
                        "detail": (
                            "Please enter Python code before "
                            "submitting."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if len(code) > 10000:
                return Response(
                    {
                        "detail": (
                            "Code is too long. Please keep "
                            "submissions under 10,000 characters."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Never execute submitted code through this API.
            submission = Submission.objects.create(
                student=request.user,
                activity=activity,
                code=code,
                status="submitted",
            )

        # ----------------------------------------------------
        # ASSIGNMENT / LAB
        # ----------------------------------------------------

        else:

            if len(response_text) > 20000:
                return Response(
                    {
                        "detail": (
                            "Your response is too long. Please "
                            "keep it under 20,000 characters."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if len(github_url) > 500:
                return Response(
                    {
                        "detail": (
                            "The GitHub URL is too long. Please "
                            "provide a valid submission URL."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if github_url and not github_url.startswith(
                (
                    "https://github.com/",
                    "http://github.com/",
                )
            ):
                return Response(
                    {
                        "detail": (
                            "Please enter a valid GitHub URL "
                            "beginning with https://github.com/"
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                attachment
                and attachment.size > 10 * 1024 * 1024
            ):
                return Response(
                    {
                        "detail": (
                            "The attachment is too large. "
                            "Please keep files under 10 MB."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            allowed_extensions = {
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
            }

            if attachment:

                extension = (
                    os.path.splitext(
                        attachment.name,
                    )[1]
                    .lower()
                    .lstrip(".")
                )

                if extension not in allowed_extensions:
                    return Response(
                        {
                            "detail": (
                                "Unsupported attachment type. "
                                "Allowed files: PDF, DOC, DOCX, TXT, "
                                "ZIP, PY, IPYNB, PNG, JPG, and JPEG."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            if (
                not response_text
                and not github_url
                and not attachment
            ):
                return Response(
                    {
                        "detail": (
                            "Please provide at least one submission "
                            "item: a written response, GitHub URL, "
                            "or attachment."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            submission = Submission.objects.create(
                student=request.user,
                activity=activity,
                code="",
                response_text=response_text,
                github_url=github_url,
                attachment=attachment,
                status="submitted",
            )

        serializer = SubmissionAPISerializer(
            submission,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "detail": "Submission created successfully.",
                "submission": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class SubmissionDetailAPIView(APIView):
    """Return one submission to its owner or an instructor/admin."""

    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def get_object(
        self,
        request,
        submission_id,
    ):

        submission = (
            Submission.objects
            .select_related(
                "student",
                "activity",
                "activity__lesson",
                "activity__lesson__course",
            )
            .filter(
                id=submission_id,
            )
            .first()
        )

        if submission is None:
            return None

        is_instructor = (
            request.user.is_staff
            or getattr(
                request.user,
                "role",
                None,
            ) == "INSTRUCTOR"
        )

        if (
            not is_instructor
            and submission.student_id != request.user.id
        ):
            return None

        return submission

    def get(
        self,
        request,
        submission_id,
    ):

        submission = self.get_object(
            request,
            submission_id,
        )

        if submission is None:
            return Response(
                {
                    "detail": "Submission not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SubmissionAPISerializer(
            submission,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class SubmissionReviewAPIView(APIView):
    """Grade a submission or mark it for correction."""

    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request,
        submission_id,
    ):

        is_instructor = (
            request.user.is_staff
            or getattr(
                request.user,
                "role",
                None,
            ) == "INSTRUCTOR"
        )

        if not is_instructor:
            return Response(
                {
                    "detail": (
                        "You do not have permission "
                        "to review submissions."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        submission = (
            Submission.objects
            .select_related(
                "student",
                "activity",
                "activity__lesson",
                "activity__lesson__course",
            )
            .filter(
                id=submission_id,
            )
            .first()
        )

        if submission is None:
            return Response(
                {
                    "detail": "Submission not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        score_value = str(
            request.data.get(
                "score",
                "",
            )
            or ""
        ).strip()

        feedback = str(
            request.data.get(
                "feedback",
                "",
            )
            or ""
        ).strip()

        review_status = str(
            request.data.get(
                "status",
                "graded",
            )
            or "graded"
        ).strip()

        if review_status not in {
            "graded",
            "correction",
        }:
            review_status = "graded"

        if score_value:

            try:
                score = int(
                    score_value,
                )
            except (
                TypeError,
                ValueError,
            ):
                return Response(
                    {
                        "detail": (
                            f"Score must be between 0 and "
                            f"{submission.activity.max_score}."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not (
                0 <= score <= submission.activity.max_score
            ):
                return Response(
                    {
                        "detail": (
                            f"Score must be between 0 and "
                            f"{submission.activity.max_score}."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            score = None

        review_changed = (
            submission.status != review_status
            or submission.score != score
            or submission.feedback != feedback
        )

        submission.score = score
        submission.feedback = feedback
        submission.status = review_status

        submission.save(
            update_fields=[
                "score",
                "feedback",
                "status",
            ]
        )

        activity_url = reverse(
            "activity_detail",
            args=[
                submission.activity.lesson.course.slug,
                submission.activity.lesson.id,
                submission.activity.id,
            ],
        )

        if review_status == "correction":

            notification_title = "CorrectionRequired"

            notification_message = (
                f"Your submission for "
                f"'{submission.activity.title}' "
                "needs correction."
            )

        else:

            notification_title = "SubmissionGraded"

            notification_message = (
                f"Your submission for "
                f"'{submission.activity.title}' "
                "has been graded."
            )

        if feedback:
            notification_message += (
                f" Instructor feedback: {feedback}"
            )

        if review_changed:
            _notify_submission_review(
                submission,
                status=review_status,
                score=score,
                feedback=feedback,
                link_url=f"/assessments/submissions/{submission.id}",
            )

        if review_status == "correction":

            ActivityCompletion.objects.filter(
                student=submission.student,
                activity=submission.activity,
            ).delete()

        elif score is not None and score >= 0:

            _mark_progress(
                submission.student,
                submission.activity,
            )

        serializer = SubmissionAPISerializer(
            submission,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "detail": (
                    "Submission marked for correction."
                    if review_status == "correction"
                    else "Submission graded successfully."
                ),
                "submission": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# QUIZ API
# ============================================================


class QuizDetailAPIView(APIView):
    """Return an authenticated student's quiz and active questions."""

    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, activity_id):

        activity = (
            Activity.objects
            .select_related(
                "lesson",
                "lesson__course",
            )
            .filter(
                id=activity_id,
                activity_type="quiz",
            )
            .first()
        )

        if activity is None:
            return Response(
                {
                    "detail": "Quiz activity not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        course = activity.lesson.course

        is_instructor = (
            request.user.is_staff
            or getattr(
                request.user,
                "role",
                None,
            ) == "INSTRUCTOR"
        )

        if not is_instructor:

            if not Enrollment.objects.filter(
                student=request.user,
                course=course,
            ).exists():

                return Response(
                    {
                        "detail": "Enrollment required.",
                        "course": {
                            "id": course.id,
                            "title": course.title,
                            "slug": course.slug,
                        },
                        "is_enrolled": False,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if not _is_activity_unlocked(
                request.user,
                activity,
            ):

                return Response(
                    {
                        "detail": "This quiz is currently locked.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        quiz = (
            Quiz.objects
            .prefetch_related(
                "questions__choices",
            )
            .filter(
                activity=activity,
            )
            .first()
        )

        if quiz is None:
            return Response(
                {
                    "detail": "Quiz configuration not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = QuizAPISerializer(
            quiz,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class QuizAttemptListCreateAPIView(APIView):
    """
    GET:
        Return the authenticated student's attempts.
        Staff/instructors may see all attempts for the quiz.

    POST:
        Create and automatically grade a new quiz attempt.
    """

    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    parser_classes = [
        JSONParser,
    ]

    def get_quiz(self, request, activity_id):

        activity = (
            Activity.objects
            .select_related(
                "lesson",
                "lesson__course",
            )
            .filter(
                id=activity_id,
                activity_type="quiz",
            )
            .first()
        )

        if activity is None:
            return None, None

        quiz = (
            Quiz.objects
            .prefetch_related(
                "questions__choices",
            )
            .filter(
                activity=activity,
            )
            .first()
        )

        return activity, quiz

    def get(self, request, activity_id):

        activity, quiz = self.get_quiz(
            request,
            activity_id,
        )

        if activity is None or quiz is None:
            return Response(
                {
                    "detail": "Quiz not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        course = activity.lesson.course

        is_instructor = (
            request.user.is_staff
            or getattr(
                request.user,
                "role",
                None,
            ) == "INSTRUCTOR"
        )

        if not is_instructor:

            if not Enrollment.objects.filter(
                student=request.user,
                course=course,
            ).exists():

                return Response(
                    {
                        "detail": "Enrollment required.",
                        "is_enrolled": False,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            attempts = QuizAttempt.objects.filter(
                quiz=quiz,
                student=request.user,
            )

        else:
            attempts = QuizAttempt.objects.filter(
                quiz=quiz,
            )

        attempts = (
            attempts
            .select_related(
                "quiz",
                "quiz__activity",
                "quiz__activity__lesson",
                "quiz__activity__lesson__course",
            )
            .prefetch_related(
                "answers__question",
                "answers__selected_choice",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

        serializer = QuizAttemptAPISerializer(
            attempts,
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "count": attempts.count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, activity_id):

        if getattr(
            request.user,
            "role",
            None,
        ) != "STUDENT":

            return Response(
                {
                    "detail": (
                        "Only students can submit quiz attempts."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        activity, quiz = self.get_quiz(
            request,
            activity_id,
        )

        if activity is None or quiz is None:
            return Response(
                {
                    "detail": "Quiz not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        course = activity.lesson.course

        if not Enrollment.objects.filter(
            student=request.user,
            course=course,
        ).exists():

            return Response(
                {
                    "detail": "Enrollment required.",
                    "course": {
                        "id": course.id,
                        "title": course.title,
                        "slug": course.slug,
                    },
                    "is_enrolled": False,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not _is_activity_unlocked(
            request.user,
            activity,
        ):

            return Response(
                {
                    "detail": "This quiz is currently locked.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        active_questions = list(
            quiz.questions
            .filter(
                is_active=True,
            )
            .order_by(
                "order",
                "id",
            )
        )

        answers_data = request.data.get(
            "answers",
            {},
        )

        if answers_data is None:
            answers_data = {}

        if not isinstance(
            answers_data,
            dict,
        ):

            return Response(
                {
                    "detail": (
                        "answers must be an object mapping "
                        "question ids to choice ids."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_points = sum(
            question.points
            for question in active_questions
        )

        earned_points = 0

        with transaction.atomic():

            attempt = QuizAttempt.objects.create(
                quiz=quiz,
                student=request.user,
                score=0,
                total_points=total_points,
                passed=False,
                completed_at=timezone.now(),
            )

            for question in active_questions:

                choice_id = answers_data.get(
                    str(question.id),
                )

                if choice_id is None:
                    choice_id = answers_data.get(
                        question.id,
                    )

                if choice_id in (
                    None,
                    "",
                ):
                    continue

                try:
                    choice_id = int(
                        choice_id,
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                selected_choice = (
                    QuizChoice.objects
                    .filter(
                        id=choice_id,
                        question=question,
                    )
                    .first()
                )

                if selected_choice is None:
                    continue

                is_correct = (
                    selected_choice.is_correct
                )

                points_awarded = (
                    question.points
                    if is_correct
                    else 0
                )

                earned_points += points_awarded

                QuizAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_choice=selected_choice,
                    is_correct=is_correct,
                    points_awarded=points_awarded,
                )

            percentage = (
                round(
                    (
                        earned_points
                        / total_points
                    ) * 100
                )
                if total_points
                else 0
            )

            passed = (
                total_points > 0
                and percentage >= quiz.passing_score
            )

            attempt.score = earned_points
            attempt.passed = passed
            attempt.completed_at = timezone.now()

            attempt.save(
                update_fields=[
                    "score",
                    "passed",
                    "completed_at",
                ]
            )

            if passed:
                _mark_progress(
                    request.user,
                    activity,
                )

        attempt = (
            QuizAttempt.objects
            .select_related(
                "quiz",
                "quiz__activity",
                "quiz__activity__lesson",
                "quiz__activity__lesson__course",
            )
            .prefetch_related(
                "answers__question",
                "answers__selected_choice",
            )
            .get(
                id=attempt.id,
            )
        )

        serializer = QuizAttemptAPISerializer(
            attempt,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "detail": "Quiz attempt submitted successfully.",
                "result": {
                    "earned_points": earned_points,
                    "total_points": total_points,
                    "percentage": percentage,
                    "passed": passed,
                    "passing_score": quiz.passing_score,
                },
                "attempt": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class QuizAttemptDetailAPIView(APIView):
    """Return one quiz attempt to its owner or an instructor/admin."""

    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, attempt_id):

        attempt = (
            QuizAttempt.objects
            .select_related(
                "quiz",
                "quiz__activity",
                "quiz__activity__lesson",
                "quiz__activity__lesson__course",
            )
            .prefetch_related(
                "answers__question",
                "answers__selected_choice",
            )
            .filter(
                id=attempt_id,
            )
            .first()
        )

        if attempt is None:
            return Response(
                {
                    "detail": "Quiz attempt not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        is_instructor = (
            request.user.is_staff
            or getattr(
                request.user,
                "role",
                None,
            ) == "INSTRUCTOR"
        )

        if (
            not is_instructor
            and attempt.student_id != request.user.id
        ):
            return Response(
                {
                    "detail": "Quiz attempt not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = QuizAttemptAPISerializer(
            attempt,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

# ============================================================
# CERTIFICATES API
# ============================================================

class CertificateListAPIView(APIView):
    """Return certificates earned by the authenticated student."""

    authentication_classes = [
        TokenAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        if getattr(
            request.user,
            "role",
            None,
        ) != "STUDENT":
            return Response(
                {
                    "detail": (
                        "Only students can access "
                        "their certificates."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        enrollments = (
            Enrollment.objects
            .filter(
                student=request.user,
            )
            .select_related(
                "course",
            )
            .order_by(
                "course__title",
            )
        )

        certificates = []

        for enrollment in enrollments:
            course = enrollment.course

            progress = _course_progress(
                request.user,
                course,
            )

            certificate_available = (
                progress["lessons_total"] > 0
                and progress["lessons_completed"]
                == progress["lessons_total"]
            )

            if not certificate_available:
                continue

            learner_name = (
                request.user.get_full_name().strip()
                or request.user.username
            )

            certificate, created = (
                Certificate.objects.get_or_create(
                    student=request.user,
                    course=course,
                    defaults={
                        "learner_name": learner_name,
                        "course_title": course.title,
                        "average_score": progress[
                            "average_score"
                        ],
                    },
                )
            )

            updates = {}

            if certificate.learner_name != learner_name:
                updates["learner_name"] = learner_name

            if certificate.course_title != course.title:
                updates["course_title"] = course.title

            if (
                certificate.average_score
                != progress["average_score"]
            ):
                updates["average_score"] = (
                    progress["average_score"]
                )

            if updates:
                Certificate.objects.filter(
                    pk=certificate.pk,
                ).update(**updates)

                certificate.refresh_from_db()

            certificates.append(
                certificate,
            )

        serializer = CertificateAPISerializer(
            certificates,
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "count": len(certificates),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
