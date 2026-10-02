from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


User = get_user_model()


class InstructorLoginAPITests(APITestCase):

    def setUp(self):
        self.instructor = User.objects.create_user(
            username="api_test_instructor",
            email="api_test_instructor@example.com",
            password="InstructorApiTest@2026!",
            role=User.Roles.INSTRUCTOR,
            is_staff=True,
        )

        self.student = User.objects.create_user(
            username="api_test_student",
            email="api_test_student@example.com",
            password="StudentApiTest@2026!",
            role=User.Roles.STUDENT,
        )

    def test_instructor_login_returns_token(self):
        response = self.client.post(
            "/api/accounts/instructor-login/",
            {
                "username": "api_test_instructor",
                "password": "InstructorApiTest@2026!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["user"]["username"],
            "api_test_instructor",
        )
        self.assertEqual(
            response.data["user"]["role"],
            "INSTRUCTOR",
        )
        self.assertTrue(response.data["user"]["is_staff"])
        self.assertEqual(len(response.data["token"]), 40)

    def test_student_cannot_use_instructor_login(self):
        response = self.client.post(
            "/api/accounts/instructor-login/",
            {
                "username": "api_test_student",
                "password": "StudentApiTest@2026!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_instructor_credentials_are_rejected(self):
        response = self.client.post(
            "/api/accounts/instructor-login/",
            {
                "username": "api_test_instructor",
                "password": "WrongPassword@2026!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
