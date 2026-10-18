import os
import tempfile
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import SimpleTestCase, override_settings

from accounts.models import PrivateInstructorDocumentStorage


class PrivateInstructorDocumentStorageTests(SimpleTestCase):
    def test_local_filesystem_storage_saves_private_document(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {
                "INSTRUCTOR_DOCUMENT_STORAGE": "filesystem",
                "INSTRUCTOR_PRIVATE_UPLOAD_ROOT": directory,
            }
            with override_settings(DEBUG=True), patch.dict(os.environ, env):
                storage = PrivateInstructorDocumentStorage()
                self.assertIsInstance(storage._backend, FileSystemStorage)

                saved = storage.save("sample-cv.pdf", ContentFile(b"test document"))
                self.assertTrue(storage.exists(saved))
                self.assertEqual(
                    storage.url(saved),
                    f"/private-instructor-documents-not-served/{saved}",
                )
                storage.delete(saved)

    def test_filesystem_backend_is_rejected_when_debug_is_false(self):
        with (
            override_settings(DEBUG=False),
            patch.dict(
                os.environ,
                {
                    "INSTRUCTOR_DOCUMENT_STORAGE": "filesystem",
                    "DJANGO_DEBUG": "False",
                },
            ),
            self.assertRaises(ImproperlyConfigured),
        ):
            PrivateInstructorDocumentStorage()

    def test_s3_backend_requires_bucket_and_region(self):
        env = {
            "INSTRUCTOR_DOCUMENT_STORAGE": "s3",
            "INSTRUCTOR_DOCUMENTS_S3_BUCKET": "",
            "INSTRUCTOR_DOCUMENTS_S3_REGION": "",
        }
        with (
            override_settings(DEBUG=False),
            patch.dict(os.environ, env),
            self.assertRaisesMessage(
                ImproperlyConfigured,
                "INSTRUCTOR_DOCUMENTS_S3_BUCKET and INSTRUCTOR_DOCUMENTS_S3_REGION",
            ),
        ):
            PrivateInstructorDocumentStorage()

    def test_partial_s3_credentials_are_rejected(self):
        env = {
            "INSTRUCTOR_DOCUMENT_STORAGE": "s3",
            "INSTRUCTOR_DOCUMENTS_S3_BUCKET": "private-test-bucket",
            "INSTRUCTOR_DOCUMENTS_S3_REGION": "auto",
            "INSTRUCTOR_DOCUMENTS_S3_ACCESS_KEY": "test-access",
            "INSTRUCTOR_DOCUMENTS_S3_SECRET_KEY": "",
            "INSTRUCTOR_DOCUMENTS_S3_SESSION_TOKEN": "",
        }
        with (
            override_settings(DEBUG=False),
            patch.dict(os.environ, env),
            self.assertRaisesMessage(
                ImproperlyConfigured,
                "Set both INSTRUCTOR_DOCUMENTS_S3_ACCESS_KEY",
            ),
        ):
            PrivateInstructorDocumentStorage()

    def test_s3_backend_receives_private_storage_options(self):
        env = {
            "INSTRUCTOR_DOCUMENT_STORAGE": "s3",
            "INSTRUCTOR_DOCUMENTS_S3_BUCKET": "private-test-bucket",
            "INSTRUCTOR_DOCUMENTS_S3_REGION": "auto",
            "INSTRUCTOR_DOCUMENTS_S3_ENDPOINT_URL": "https://storage.example.test",
            "INSTRUCTOR_DOCUMENTS_S3_PREFIX": "instructor-documents",
            "INSTRUCTOR_DOCUMENTS_S3_ACCESS_KEY": "test-access",
            "INSTRUCTOR_DOCUMENTS_S3_SECRET_KEY": "test-secret",
            "INSTRUCTOR_DOCUMENTS_S3_SESSION_TOKEN": "",
            "INSTRUCTOR_DOCUMENTS_S3_QUERYSTRING_EXPIRE": "240",
        }
        with (
            override_settings(DEBUG=False),
            patch.dict(os.environ, env),
            patch("storages.backends.s3.S3Storage") as mocked_s3,
        ):
            PrivateInstructorDocumentStorage()
            options = mocked_s3.call_args.kwargs
            self.assertEqual(options["bucket_name"], "private-test-bucket")
            self.assertEqual(options["region_name"], "auto")
            self.assertEqual(
                options["endpoint_url"], "https://storage.example.test"
            )
            self.assertEqual(options["location"], "instructor-documents")
            self.assertIsNone(options["default_acl"])
            self.assertTrue(options["querystring_auth"])
            self.assertEqual(options["querystring_expire"], 240)
            self.assertFalse(options["file_overwrite"])
            self.assertEqual(
                options["object_parameters"]["CacheControl"],
                "private, no-store",
            )

    def test_unknown_storage_mode_is_rejected(self):
        with (
            override_settings(DEBUG=True),
            patch.dict(os.environ, {"INSTRUCTOR_DOCUMENT_STORAGE": "unknown"}),
            self.assertRaisesMessage(
                ImproperlyConfigured,
                "INSTRUCTOR_DOCUMENT_STORAGE must be",
            ),
        ):
            PrivateInstructorDocumentStorage()
