from django.urls import path

from .views import (
    InstructorLoginAPIView,
    StudentLoginAPIView,
)


urlpatterns = [
    path(
        "login/",
        StudentLoginAPIView.as_view(),
        name="student-login",
    ),
    path(
        "instructor-login/",
        InstructorLoginAPIView.as_view(),
        name="instructor-login",
    ),
]
