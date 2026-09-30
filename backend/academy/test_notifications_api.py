from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Notification


User = get_user_model()


class NotificationAPITests(TestCase):

    def setUp(self):
        self.student = User.objects.create_user(
            username="api_student",
            password="StrongPass123!",
            role="STUDENT",
        )

        self.other_student = User.objects.create_user(
            username="api_other_student",
            password="StrongPass123!",
            role="STUDENT",
        )

        self.token = Token.objects.create(
            user=self.student,
        )

        self.client = APIClient()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}",
        )

    def test_notification_list_returns_only_current_users_notifications(self):
        Notification.objects.create(
            recipient=self.student,
            notification_type="graded",
            title="My notification",
            message="My message.",
        )

        Notification.objects.create(
            recipient=self.other_student,
            notification_type="graded",
            title="Private notification",
            message="Other student's message.",
        )

        response = self.client.get(
            reverse("api-notifications"),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["results"][0]["title"],
            "My notification",
        )

    def test_unread_notification_endpoint_returns_only_unread(self):
        Notification.objects.create(
            recipient=self.student,
            notification_type="graded",
            title="Unread",
            message="Unread message.",
            is_read=False,
        )

        Notification.objects.create(
            recipient=self.student,
            notification_type="graded",
            title="Read",
            message="Read message.",
            is_read=True,
        )

        response = self.client.get(
            reverse("api-notifications-unread"),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["results"][0]["title"],
            "Unread",
        )

    def test_notification_read_endpoint_marks_only_owned_notification_read(self):
        notification = Notification.objects.create(
            recipient=self.student,
            notification_type="correction",
            title="Correction Required",
            message="Please correct your work.",
            is_read=False,
        )

        response = self.client.post(
            reverse(
                "api-notification-read",
                args=[notification.id],
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        notification.refresh_from_db()

        self.assertTrue(
            notification.is_read,
        )

        self.assertTrue(
            response.data["is_read"],
        )

    def test_notification_read_endpoint_rejects_other_users_notification(self):
        notification = Notification.objects.create(
            recipient=self.other_student,
            notification_type="graded",
            title="Private",
            message="Private notification.",
            is_read=False,
        )

        response = self.client.post(
            reverse(
                "api-notification-read",
                args=[notification.id],
            ),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        notification.refresh_from_db()

        self.assertFalse(
            notification.is_read,
        )

    def test_notification_api_requires_authentication(self):
        self.client.credentials()

        response = self.client.get(
            reverse("api-notifications"),
        )

        self.assertEqual(
            response.status_code,
            401,
        )
