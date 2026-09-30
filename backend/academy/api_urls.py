from django.urls import path

from .api_views import (
    CourseDetailAPIView,
    CourseListAPIView,
    CourseProgressAPIView,
    NotificationListAPIView,
    NotificationReadAPIView,
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
        "courses/<slug:slug>/progress/",
        CourseProgressAPIView.as_view(),
        name="api-course-progress",
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
