from django.urls import path

from .views import (
    InstructorLoginAPIView,
    StudentRegistrationAPIView,
    StudentLoginAPIView,
)


urlpatterns = [
    path("register/", StudentRegistrationAPIView.as_view(), name="student-register"),
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
