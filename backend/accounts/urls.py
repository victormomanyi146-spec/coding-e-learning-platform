from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path(
        "login/",
        (
            views.react_login_redirect
            if settings.UNIFIED_REACT_FRONTEND
            else auth_views.LoginView.as_view(
                template_name="accounts/login.html"
            )
        ),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    path(
        "register/",
        views.register,
        name="register",
    ),
]
