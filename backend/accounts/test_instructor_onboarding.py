import re
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import InstructorApplication

User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {
        "instructor_application": "100/hour",
        "instructor_otp_verify": "100/hour",
        "instructor_otp_resend": "100/hour",
    }},
)
class InstructorOnboardingAPITests(APITestCase):
    create_url = "/api/accounts/instructor-applications/"
    verify_url = "/api/accounts/instructor-applications/verify-otp/"
    list_url = "/api/accounts/admin/instructor-applications/"

    def setUp(self):
        cache.clear()
        if hasattr(mail, "outbox"):
            mail.outbox.clear()
        self.applications_for_cleanup = []
        self.admin = User.objects.create_superuser(
            username="review_admin", email="review_admin@example.com", password="AdminStrong@2026!",
        )
        self.admin_token = Token.objects.create(user=self.admin)

    def tearDown(self):
        for application in self.applications_for_cleanup:
            for field_name in ("cv", "qualification_document"):
                uploaded = getattr(application, field_name, None)
                if uploaded and uploaded.name:
                    uploaded.delete(save=False)
        super().tearDown()

    def submit(self, username="applicant_one", email="applicant_one@example.com"):
        data = {
            "username": username,
            "email": email,
            "password": "ApplicantStrong@2026!",
            "password_confirm": "ApplicantStrong@2026!",
            "qualification": "BSc Computer Science",
            "awarding_institution": "Example University",
            "experience_summary": "Five years building and teaching software engineering projects.",
            "cv": SimpleUploadedFile("applicant-cv.pdf", b"%PDF-1.4 test document", content_type="application/pdf"),
        }
        response = self.client.post(self.create_url, data, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        application = InstructorApplication.objects.get(pk=response.data["application_id"])
        self.applications_for_cleanup.append(application)
        return application

    def otp_for_latest_email(self):
        self.assertTrue(mail.outbox)
        match = re.search(r"verification code is (\d{6})", mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def verify(self, application):
        response = self.client.post(self.verify_url, {"application_id": application.id, "otp": self.otp_for_latest_email()}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        application.refresh_from_db()
        return response

    def test_application_sends_otp_and_starts_inactive(self):
        application = self.submit()
        self.assertEqual(application.status, InstructorApplication.Status.PENDING_EMAIL)
        self.assertFalse(application.user.is_active)
        self.assertEqual(application.user.role, User.Roles.STUDENT)
        self.assertEqual(len(mail.outbox), 1)

    def test_verified_applicant_waits_for_admin_and_cannot_login_as_student(self):
        application = self.submit()
        self.verify(application)
        self.assertEqual(application.status, InstructorApplication.Status.PENDING_REVIEW)
        application.user.refresh_from_db()
        self.assertFalse(application.user.is_active)
        self.assertEqual(application.user.role, User.Roles.STUDENT)
        login_response = self.client.post("/api/accounts/login/", {"username": application.user.username, "password": "ApplicantStrong@2026!"}, format="json")
        self.assertEqual(login_response.status_code, 400)
        instructor_response = self.client.post("/api/accounts/instructor-login/", {"username": application.user.username, "password": "ApplicantStrong@2026!"}, format="json")
        self.assertEqual(instructor_response.status_code, 400)

    def test_only_superuser_can_review_and_approval_grants_instructor_role(self):
        application = self.submit()
        self.verify(application)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        review = self.client.post(f"/api/accounts/admin/instructor-applications/{application.id}/review/", {"decision": "approve", "admin_notes": "Credentials checked."}, format="json")
        self.assertEqual(review.status_code, 200, review.data)
        application.user.refresh_from_db()
        application.refresh_from_db()
        self.assertEqual(application.status, InstructorApplication.Status.APPROVED)
        self.assertEqual(application.user.role, User.Roles.INSTRUCTOR)
        self.assertTrue(application.user.is_staff)
        self.assertTrue(application.user.is_active)
        login_response = self.client.post("/api/accounts/instructor-login/", {"username": application.user.username, "password": "ApplicantStrong@2026!"}, format="json")
        self.assertEqual(login_response.status_code, 200, login_response.data)

    def test_instructor_staff_account_cannot_access_admin_review_api(self):
        application = self.submit()
        self.verify(application)
        instructor = User.objects.create_user(username="staff_instructor", email="staff@example.com", password="InstructorStrong@2026!", role=User.Roles.INSTRUCTOR, is_staff=True)
        token = Token.objects.create(user=instructor)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

    def test_unverified_application_cannot_be_approved(self):
        application = self.submit()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        response = self.client.post(f"/api/accounts/admin/instructor-applications/{application.id}/review/", {"decision": "approve"}, format="json")
        self.assertEqual(response.status_code, 400)
        application.user.refresh_from_db()
        self.assertEqual(application.user.role, User.Roles.STUDENT)
        self.assertFalse(application.user.is_active)

    def test_rejected_application_is_deactivated(self):
        application = self.submit()
        self.verify(application)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        response = self.client.post(f"/api/accounts/admin/instructor-applications/{application.id}/review/", {"decision": "reject", "admin_notes": "Please provide a recognized qualification."}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        application.refresh_from_db()
        application.user.refresh_from_db()
        self.assertEqual(application.status, InstructorApplication.Status.REJECTED)
        self.assertFalse(application.user.is_active)
        self.assertFalse(application.user.is_staff)
