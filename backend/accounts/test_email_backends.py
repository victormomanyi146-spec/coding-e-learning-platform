import json
from io import BytesIO
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.test import SimpleTestCase, override_settings

from .email_backends import (
    RESEND_EMAILS_URL,
    ResendAPIEmailBackend,
    ResendAPIEmailError,
)


class ResendAPIEmailBackendTests(SimpleTestCase):
    @override_settings(RESEND_API_KEY="re_test_private_key")
    def test_sends_plain_text_email_over_https(self):
        response = BytesIO(b'{"id":"email_test_123"}')
        response.status = 200
        message = EmailMessage(
            subject="Verify your Tech Haven instructor application",
            body="Your verification code is 123456.",
            from_email="Tech Haven <onboarding@resend.dev>",
            to=["account-owner@example.com"],
        )

        with patch("accounts.email_backends.urlopen", return_value=response) as mocked:
            sent = ResendAPIEmailBackend().send_messages([message])

        self.assertEqual(sent, 1)
        mocked.assert_called_once()
        request = mocked.call_args.args[0]
        kwargs = mocked.call_args.kwargs
        self.assertEqual(request.full_url, RESEND_EMAILS_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer re_test_private_key")
        self.assertEqual(kwargs["timeout"], 8)
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["from"], "Tech Haven <onboarding@resend.dev>")
        self.assertEqual(payload["to"], ["account-owner@example.com"])
        self.assertEqual(payload["subject"], "Verify your Tech Haven instructor application")
        self.assertEqual(payload["text"], "Your verification code is 123456.")
        self.assertNotIn("html", payload)

    @override_settings(RESEND_API_KEY="re_test_private_key")
    def test_includes_html_cc_bcc_and_reply_to_when_present(self):
        response = BytesIO(b'{"id":"email_test_456"}')
        response.status = 200
        message = EmailMultiAlternatives(
            subject="Tech Haven update",
            body="Plain-text update",
            from_email="Tech Haven <onboarding@resend.dev>",
            to=["account-owner@example.com"],
            cc=["copy@example.com"],
            bcc=["hidden@example.com"],
            reply_to=["support@example.com"],
        )
        message.attach_alternative("<p>HTML update</p>", "text/html")

        with patch("accounts.email_backends.urlopen", return_value=response) as mocked:
            self.assertEqual(ResendAPIEmailBackend().send_messages([message]), 1)

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["text"], "Plain-text update")
        self.assertEqual(payload["html"], "<p>HTML update</p>")
        self.assertEqual(payload["cc"], ["copy@example.com"])
        self.assertEqual(payload["bcc"], ["hidden@example.com"])
        self.assertEqual(payload["reply_to"], ["support@example.com"])

    @override_settings(RESEND_API_KEY="")
    def test_requires_api_key_and_does_not_make_request(self):
        message = EmailMessage("subject", "body", "from@example.com", ["to@example.com"])
        with patch("accounts.email_backends.urlopen") as mocked:
            with self.assertRaisesMessage(
                ImproperlyConfigured,
                "RESEND_API_KEY must be set",
            ):
                ResendAPIEmailBackend().send_messages([message])
        mocked.assert_not_called()

    @override_settings(RESEND_API_KEY="re_test_private_key")
    def test_http_error_is_reported_without_exposing_response_body_or_key(self):
        error = HTTPError(
            RESEND_EMAILS_URL,
            401,
            "Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"message":"invalid api key"}'),
        )
        message = EmailMessage("subject", "body", "from@example.com", ["to@example.com"])
        with patch("accounts.email_backends.urlopen", side_effect=error):
            with self.assertRaisesRegex(ResendAPIEmailError, "HTTP 401") as raised:
                ResendAPIEmailBackend().send_messages([message])
        self.assertNotIn("re_test_private_key", str(raised.exception))
        self.assertNotIn("invalid api key", str(raised.exception))

    @override_settings(RESEND_API_KEY="re_test_private_key")
    def test_network_error_is_reported_and_fail_silently_returns_zero(self):
        message = EmailMessage("subject", "body", "from@example.com", ["to@example.com"])
        with patch("accounts.email_backends.urlopen", side_effect=URLError("network unavailable")):
            with self.assertRaisesRegex(ResendAPIEmailError, "over HTTPS"):
                ResendAPIEmailBackend().send_messages([message])

        with patch("accounts.email_backends.urlopen", side_effect=URLError("network unavailable")):
            backend = ResendAPIEmailBackend(fail_silently=True)
            self.assertEqual(backend.send_messages([message]), 0)

    @override_settings(RESEND_API_KEY="re_test_private_key")
    def test_empty_message_list_needs_no_api_key_or_network(self):
        with patch("accounts.email_backends.urlopen") as mocked:
            self.assertEqual(ResendAPIEmailBackend().send_messages([]), 0)
        mocked.assert_not_called()
