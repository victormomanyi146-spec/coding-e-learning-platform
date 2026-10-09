from django.http import HttpResponseForbidden


class BlockInstructorFromDjangoAdminMiddleware:
    """Prevent instructor accounts from accessing Django's built-in admin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        user = getattr(request, "user", None)
        is_admin_path = path == "/admin" or path.startswith("/admin/")

        if (
            is_admin_path
            and user is not None
            and user.is_authenticated
            and getattr(user, "role", None) == "INSTRUCTOR"
        ):
            return HttpResponseForbidden(
                "Instructor accounts cannot access Django administration."
            )

        return self.get_response(request)
