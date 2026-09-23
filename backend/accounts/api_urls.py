from django.urls import path

from .views import StudentLoginAPIView


urlpatterns = [
    path("login/", StudentLoginAPIView.as_view(), name="student-login"),
]
