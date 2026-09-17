from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class AccountApiTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student",
            password="StrongPass123!",
            role="STUDENT",
        )

    def test_student_login_returns_token(self):
        response = self.client.post(
            reverse("student-login"),
            {
                "username": "student",
                "password": "StrongPass123!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())

    def test_non_student_cannot_use_student_login(self):
        instructor = User.objects.create_user(
            username="instructor",
            password="StrongPass123!",
            role="INSTRUCTOR",
        )

        response = self.client.post(
            reverse("student-login"),
            {
                "username": instructor.username,
                "password": "StrongPass123!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
