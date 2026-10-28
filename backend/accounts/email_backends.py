"""Django email backend using the Resend REST API over HTTPS.

This avoids SMTP ports, which are blocked for Render Free web services.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend

RESEND_EMAILS_URL = "https://api.resend.com/emails"
REQUEST_TIMEOUT_SECONDS = 8


class ResendAPIEmailError(RuntimeError):
    """Raised when the Resend API cannot accept an email message."""


class ResendAPIEmailBackend(BaseEmailBackend):
    """Send Django EmailMessage objects with the Resend HTTPS API."""

    def send_messages(self, email_messages):
        messages = list(email_messages or [])
        if not messages:
            return 0

        api_key = getattr(settings, "RESEND_API_KEY", "")
        if not api_key:
            raise ImproperlyConfigured(
                "RESEND_API_KEY must be set when using ResendAPIEmailBackend."
            )

        sent_count = 0
        for message in messages:
            try:
                self._send_message(message, api_key)
            except ResendAPIEmailError:
                if self.fail_silently:
                    continue
                raise
            sent_count += 1
        return sent_count

    @staticmethod
    def _payload_for(message):
        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": list(message.to or []),
            "subject": message.subject or "",
        }

        body = message.body or ""
        if getattr(message, "content_subtype", "plain").lower() == "html":
            payload["html"] = body
        else:
            payload["text"] = body

        for alternative, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype.lower() == "text/html":
                payload["html"] = alternative
                break

        for field in ("cc", "bcc", "reply_to"):
            values = getattr(message, field, None)
            if values:
                payload[field] = list(values)

        return payload

    @classmethod
    def _send_message(cls, message, api_key):
        body = json.dumps(cls._payload_for(message)).encode("utf-8")
        request = Request(
            RESEND_EMAILS_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                status_code = getattr(response, "status", 200)
                response.read()
        except HTTPError as exc:
            status_code = exc.code
            exc.close()
            raise ResendAPIEmailError(
                f"Resend API rejected the email (HTTP {status_code})."
            ) from None
        except (URLError, TimeoutError, OSError):
            raise ResendAPIEmailError(
                "Could not reach the Resend email API over HTTPS."
            ) from None

        if not 200 <= status_code < 300:
            raise ResendAPIEmailError(
                f"Resend API returned an unexpected HTTP status ({status_code})."
            )
