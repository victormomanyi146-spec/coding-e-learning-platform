from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

User = get_user_model()


class AdminAccountManagementAPITests(APITestCase):
    list_url = "/api/accounts/admin/users/"

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="account_admin", email="account_admin@example.com", password="AdminStrong@2026!"
        )
        self.admin_token = Token.objects.create(user=self.admin)
        self.student = User.objects.create_user(
            username="learner_one", email="learner@example.com", password="StudentStrong@2026!", role=User.Roles.STUDENT
        )
        self.instructor = User.objects.create_user(
            username="teacher_one", email="teacher@example.com", password="InstructorStrong@2026!", role=User.Roles.INSTRUCTOR, is_staff=True
        )
        self.inactive = User.objects.create_user(
            username="paused_user", email="paused@example.com", password="StudentStrong@2026!", role=User.Roles.STUDENT, is_active=False
        )

    def authenticate_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

    def test_superuser_can_search_and_filter_accounts(self):
        self.authenticate_admin()
        response = self.client.get(self.list_url, {"q": "learner", "role": "STUDENT", "status": "ACTIVE"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["username"], "learner_one")
        self.assertEqual(response.data["results"][0]["role"], "STUDENT")
        self.assertEqual(response.data["summary"]["total"], 4)

    def test_non_superuser_cannot_read_accounts(self):
        user_token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {user_token.key}")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

    def test_deactivating_account_revokes_token(self):
        self.authenticate_admin()
        target_token = Token.objects.create(user=self.student)
        response = self.client.patch(
            f"{self.list_url}{self.student.id}/", {"is_active": False, "reason": "Test account access suspension."}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
        self.assertFalse(Token.objects.filter(pk=target_token.pk).exists())
        self.assertEqual(response.data["account"]["is_active"], False)

    def test_admin_cannot_deactivate_superuser_from_account_screen(self):
        self.authenticate_admin()
        response = self.client.patch(
            f"{self.list_url}{self.admin.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_only_is_active_boolean_is_accepted(self):
        self.authenticate_admin()
        response = self.client.patch(
            f"{self.list_url}{self.student.id}/", {"role": "INSTRUCTOR"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.Roles.STUDENT)

    def test_instructor_is_not_returned_as_admin(self):
        self.authenticate_admin()
        response = self.client.get(self.list_url, {"role": "INSTRUCTOR"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["username"] for row in response.data["results"]], ["teacher_one"])
        self.assertEqual(response.data["results"][0]["role"], "INSTRUCTOR")
