from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


User = get_user_model()


class StudentRegistrationAPITests(APITestCase):
    url = "/api/accounts/register/"

    def registration_data(self, **overrides):
        data = {
            "username": "new_student",
            "email": "new_student@example.com",
            "password": "G7!green-forest-Cloud",
            "password_confirm": "G7!green-forest-Cloud",
        }
        data.update(overrides)
        return data

    def test_registration_creates_student_and_returns_token(self):
        response = self.client.post(
            self.url, self.registration_data(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="new_student")
        self.assertEqual(user.role, User.Roles.STUDENT)
        self.assertTrue(user.check_password("G7!green-forest-Cloud"))
        self.assertEqual(response.data["token"], Token.objects.get(user=user).key)
        self.assertEqual(response.data["user"]["username"], user.username)

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            self.url,
            self.registration_data(password_confirm="different-password"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="new_student").exists())

    def test_registration_rejects_duplicate_username(self):
        User.objects.create_user(
            username="new_student",
            email="existing@example.com",
            password="G7!green-forest-Cloud",
            role=User.Roles.STUDENT,
        )

        response = self.client.post(
            self.url,
            self.registration_data(email="another@example.com"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_cannot_assign_instructor_role(self):
        response = self.client.post(
            self.url,
            self.registration_data(role="INSTRUCTOR"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="new_student")
        self.assertEqual(user.role, User.Roles.STUDENT)
