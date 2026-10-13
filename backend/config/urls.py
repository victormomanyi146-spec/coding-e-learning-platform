from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.http import HttpResponse
from django.shortcuts import render

from academy.models import Course


def home(request):
    """Display the public Coding Academy landing page."""
    courses = Course.objects.all().order_by("created_at", "title")
    return render(request, "home.html", {"courses": courses})


def react_app(request):
    """Serve the bundled React single-page application."""
    return render(request, "react_app/index.html")


def healthz(request):
    """Expose a lightweight application health check."""
    return HttpResponse("ok", content_type="text/plain")


# Explicit React admin routes must precede Django's broad `admin/` include.
# They are enabled only for the Docker/unified React deployment; the existing
# native Python Render service keeps its current Django-admin routing.
urlpatterns = []
if settings.UNIFIED_REACT_FRONTEND:
    urlpatterns += [
        re_path(r"^admin/overview/?$", react_app, name="react-admin-overview"),
        re_path(r"^admin/accounts/?$", react_app, name="react-admin-accounts"),
        re_path(r"^admin/audit-log/?$", react_app, name="react-admin-audit-log"),
        re_path(
            r"^admin/instructor-applications/?$",
            react_app,
            name="react-admin-instructor-applications",
        ),
        re_path(
            r"^admin/learning-management/?$",
            react_app,
            name="react-admin-learning-management",
        ),
    ]

urlpatterns += [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("api/accounts/", include("accounts.api_urls")),
    path("api/", include("academy.api_urls")),
    path("healthz/", healthz, name="healthz"),
]

if settings.UNIFIED_REACT_FRONTEND:
    urlpatterns += [
        re_path(r"^courses/?$", react_app, name="react-courses"),
        re_path(
            r"^courses/[^/]+/lessons/[^/]+/activities/[^/]+/?$",
            react_app,
            name="react-course-activity",
        ),
        re_path(
            r"^courses/[^/]+/quiz/[^/]+/?$",
            react_app,
            name="react-course-quiz",
        ),
        re_path(
            r"^courses/(?!(?:assessments|notifications|instructor)(?:/|$))[^/]+/?$",
            react_app,
            name="react-course-detail",
        ),
        path("courses/", include("academy.urls")),
    ]

    urlpatterns += [
        path("", react_app, name="home"),
        re_path(
            r"^(?!admin/|accounts/|api/|static/|media/|healthz/).*$",
            react_app,
            name="react-app",
        ),
    ]
else:
    urlpatterns += [
        path("", home, name="home"),
        path("courses/", include("academy.urls")),
    ]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
