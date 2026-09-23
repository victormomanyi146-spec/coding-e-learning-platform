from django.contrib import admin
from django.urls import include, path
from django.shortcuts import render

from academy.models import Course


def home(request):
    """Display the public Coding Academy landing page."""
    courses = Course.objects.all().order_by("created_at", "title")
    return render(request, "home.html", {"courses": courses})


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("api/accounts/", include("accounts.api_urls")),
    path("courses/", include("academy.urls")),
]
