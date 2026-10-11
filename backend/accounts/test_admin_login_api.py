from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

User = get_user_model()


class AdminLoginAPITests(APITestCase):
    url = "/api/accounts/admin-login/"
    password = "AdminLoginTest@2026!Strong"

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="login_test_admin",
            email="login_test_admin@example.com",
            password=self.password,
        )
        self.student = User.objects.create_user(
            username="login_test_student",
            email="login_test_student@example.com",
            password="StudentLoginTest@2026!Strong",
            role=User.Roles.STUDENT,
        )
        self.instructor = User.objects.create_user(
            username="login_test_instructor",
            email="login_test_instructor@example.com",
            password="InstructorLoginTest@2026!Strong",
            role=User.Roles.INSTRUCTOR,
            is_staff=True,
        )

    def test_superuser_receives_admin_role_and_token(self):
        response = self.client.post(
            self.url,
            {"username": self.admin.username, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "ADMIN")
        self.assertEqual(response.data["token"], Token.objects.get(user=self.admin).key)

    def test_student_cannot_use_admin_login(self):
        response = self.client.post(
            self.url,
            {"username": self.student.username, "password": "StudentLoginTest@2026!Strong"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_instructor_cannot_use_admin_login(self):
        response = self.client.post(
            self.url,
            {"username": self.instructor.username, "password": "InstructorLoginTest@2026!Strong"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_superuser_cannot_sign_in_through_student_endpoint(self):
        response = self.client.post(
            "/api/accounts/login/",
            {"username": self.admin.username, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
