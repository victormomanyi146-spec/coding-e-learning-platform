from django.conf import settings
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import Resolver404, resolve
from unittest import skipUnless

from .views import react_login_redirect


class LegacyLoginRedirectViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_preserves_next_parameter(self):
        request = self.factory.get("/accounts/login/?next=/courses/")
        response = react_login_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/login/?next=%2Fcourses%2F")

    def test_without_next_redirects_to_react_login(self):
        request = self.factory.get("/accounts/login/")
        response = react_login_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/login/")


@skipUnless(
    settings.UNIFIED_REACT_FRONTEND,
    "Run route integration tests with UNIFIED_REACT_FRONTEND=True.",
)
class UnifiedReactRouteTests(TestCase):
    def test_legacy_login_url_redirects_to_react_and_preserves_next(self):
        response = self.client.get("/accounts/login/?next=/courses/")
        self.assertRedirects(
            response,
            "/login/?next=%2Fcourses%2F",
            fetch_redirect_response=False,
        )

    def test_react_admin_pages_resolve_to_spa_before_django_admin(self):
        paths = (
            "/admin/overview",
            "/admin/accounts/",
            "/admin/audit-log",
            "/admin/instructor-applications/",
            "/admin/learning-management",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(resolve(path).func.__name__, "react_app")

    def test_django_admin_login_stays_on_django_admin(self):
        match = resolve("/admin/login/")
        self.assertEqual(match.namespace, "admin")
        self.assertEqual(match.url_name, "login")

    def test_react_login_route_resolves_through_spa_fallback(self):
        self.assertEqual(resolve("/login").func.__name__, "react_app")
