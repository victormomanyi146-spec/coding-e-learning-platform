from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from accounts.models import AdminAuditLog, InstructorApplication
from academy.models import Certificate, Course, Enrollment, Submission

User = get_user_model()


class AdminOverviewAndAuditTests(APITestCase):
    overview_url = "/api/accounts/admin/overview/"
    audit_url = "/api/accounts/admin/audit-log/"
    accounts_url = "/api/accounts/admin/users/"

    def setUp(self):
        self.admin = User.objects.create_superuser(username="overview_admin", email="overview_admin@example.com", password="AdminStrong@2026!")
        self.token = Token.objects.create(user=self.admin)
        self.student = User.objects.create_user(username="overview_student", email="student@example.com", password="StudentStrong@2026!", role=User.Roles.STUDENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_overview_returns_live_platform_counts(self):
        Course.objects.create(title="Audit Test Course", slug="audit-test-course", description="Test", instructor="Instructor", duration="1 week", level="Beginner")
        response = self.client.get(self.overview_url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["summary"]["total_accounts"], 2)
        self.assertEqual(response.data["summary"]["administrators"], 1)
        self.assertEqual(response.data["summary"]["students"], 1)
        self.assertEqual(response.data["summary"]["courses"], 1)
        self.assertIn("recent_audit_events", response.data)

    def test_account_change_requires_reason_and_creates_audit_event(self):
        response = self.client.patch(f"{self.accounts_url}{self.student.id}/", {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AdminAuditLog.objects.count(), 0)

        response = self.client.patch(
            f"{self.accounts_url}{self.student.id}/",
            {"is_active": False, "reason": "Test account access suspension."},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        event = AdminAuditLog.objects.get()
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.actor_username, "overview_admin")
        self.assertEqual(event.target, self.student)
        self.assertEqual(event.target_username, "overview_student")
        self.assertEqual(event.action, AdminAuditLog.Actions.DEACTIVATED)
        self.assertEqual(event.reason, "Test account access suspension.")

    def test_audit_log_is_searchable_and_lists_who_when_and_why(self):
        self.client.patch(
            f"{self.accounts_url}{self.student.id}/",
            {"is_active": False, "reason": "Temporary test suspension."},
            format="json",
        )
        response = self.client.get(self.audit_url, {"q": "Temporary test", "action": "DEACTIVATED"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        event = response.data["results"][0]
        self.assertEqual(event["actor_username"], "overview_admin")
        self.assertEqual(event["target_username"], "overview_student")
        self.assertEqual(event["reason"], "Temporary test suspension.")
        self.assertTrue(event["created_at"])

    def test_non_superuser_cannot_read_overview_or_audit_log(self):
        student_token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {student_token.key}")
        self.assertEqual(self.client.get(self.overview_url).status_code, 403)
        self.assertEqual(self.client.get(self.audit_url).status_code, 403)

    def test_reactivation_is_also_audited(self):
        self.student.is_active = False
        self.student.save(update_fields=["is_active"])
        response = self.client.patch(
            f"{self.accounts_url}{self.student.id}/",
            {"is_active": True, "reason": "Access restored after review."},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        event = AdminAuditLog.objects.get()
        self.assertEqual(event.action, AdminAuditLog.Actions.ACTIVATED)
        self.assertEqual(event.reason, "Access restored after review.")
