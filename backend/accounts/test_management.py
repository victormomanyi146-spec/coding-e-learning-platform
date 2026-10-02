from io import StringIO
import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch


User = get_user_model()


class CreateInstructorCommandTests(TestCase):

    def test_instructor_bootstrap_assigns_admin_permissions(self):
        env = {
            "DJANGO_INSTRUCTOR_USERNAME": "test_instructor",
            "DJANGO_INSTRUCTOR_EMAIL": "test_instructor@example.com",
            "DJANGO_INSTRUCTOR_PASSWORD": "StrongInstructorPass123!",
        }

        output = StringIO()

        with patch.dict(os.environ, env, clear=False):
            call_command(
                "create_instructor",
                stdout=output,
            )

        user = User.objects.get(username="test_instructor")

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, User.Roles.INSTRUCTOR)

        self.assertTrue(
            user.has_perm("accounts.view_user")
        )
        self.assertTrue(
            user.has_perm("accounts.change_user")
        )
        self.assertTrue(
            user.has_perm("academy.view_course")
        )
        self.assertTrue(
            user.has_perm("academy.change_course")
        )

        self.assertFalse(
            user.has_perm("academy.delete_course")
        )
