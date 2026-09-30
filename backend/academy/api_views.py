from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import serializers

from .models import (
    Course,
    Enrollment,
    Notification,
)
from .api_serializers import (
    CourseDetailAPISerializer,
    CourseListAPISerializer,
)

from .views import (
    _course_progress,
    _lesson_is_completed,
    _module_progress,
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

