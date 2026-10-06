from django.urls import path

from .api_views import (
    CourseDetailAPIView,
    CourseEnrollAPIView,
    CourseListAPIView,
    CourseProgressAPIView,
    ActivityCompleteAPIView,
    NotificationListAPIView,
    NotificationReadAPIView,
    QuizAttemptDetailAPIView,
    QuizAttemptListCreateAPIView,
    QuizDetailAPIView,
    SubmissionDetailAPIView,
    SubmissionListCreateAPIView,
    SubmissionReviewAPIView,
    UnreadNotificationListAPIView,
)


urlpatterns = [

    path(
        "courses/",
        CourseListAPIView.as_view(),
        name="api-course-list",
    ),

    path(
        "courses/<slug:slug>/",
        CourseDetailAPIView.as_view(),
        name="api-course-detail",
    ),

    path(
        "courses/<slug:slug>/enroll/",
        CourseEnrollAPIView.as_view(),
        name="api-course-enroll",
    ),

    path(
        "courses/<slug:slug>/progress/",
        CourseProgressAPIView.as_view(),
        name="api-course-progress",
    ),

    path(
        "activities/<int:activity_id>/complete/",
        ActivityCompleteAPIView.as_view(),
        name="api-activity-complete",
    ),

    path(
        "quizzes/<int:activity_id>/",
        QuizDetailAPIView.as_view(),
        name="api-quiz-detail",
    ),

    path(
        "quizzes/<int:activity_id>/attempts/",
        QuizAttemptListCreateAPIView.as_view(),
        name="api-quiz-attempt-list-create",
    ),

    path(
        "quizzes/attempts/<int:attempt_id>/",
        QuizAttemptDetailAPIView.as_view(),
        name="api-quiz-attempt-detail",
    ),

    path(
        "submissions/",
        SubmissionListCreateAPIView.as_view(),
        name="api-submission-list-create",
    ),

    path(
        "submissions/<int:submission_id>/",
        SubmissionDetailAPIView.as_view(),
        name="api-submission-detail",
    ),

    path(
        "submissions/<int:submission_id>/review/",
        SubmissionReviewAPIView.as_view(),
        name="api-submission-review",
    ),

    path(
        "notifications/",
        NotificationListAPIView.as_view(),
        name="api-notifications",
    ),

    path(
        "notifications/unread/",
        UnreadNotificationListAPIView.as_view(),
        name="api-notifications-unread",
    ),

    path(
        "notifications/<int:notification_id>/read/",
        NotificationReadAPIView.as_view(),
        name="api-notification-read",
    ),

]
