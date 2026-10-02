import os

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = "Create or update the deployment instructor account from environment variables."

    def handle(self, *args, **options):
        username = os.environ.get(
            "DJANGO_INSTRUCTOR_USERNAME",
            "",
        ).strip()

        email = os.environ.get(
            "DJANGO_INSTRUCTOR_EMAIL",
            "",
        ).strip()

        password = os.environ.get(
            "DJANGO_INSTRUCTOR_PASSWORD",
            "",
        )

        if not username and not email and not password:
            self.stdout.write(
                self.style.WARNING(
                    "Instructor bootstrap skipped: deployment instructor "
                    "environment variables are not configured."
                )
            )
            return

        if not username:
            raise CommandError(
                "DJANGO_INSTRUCTOR_USERNAME must be set."
            )

        if not password:
            raise CommandError(
                "DJANGO_INSTRUCTOR_PASSWORD must be set."
            )

        if len(password) < 12:
            raise CommandError(
                "DJANGO_INSTRUCTOR_PASSWORD must contain at least "
                "12 characters."
            )

        if not email:
            email = f"{username}@example.invalid"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "role": User.Roles.INSTRUCTOR,
                "is_staff": True,
                "is_active": True,
            },
        )

        user.email = email
        user.role = User.Roles.INSTRUCTOR
        user.is_staff = True
        user.is_active = True
        user.set_password(password)
        user.save(
            update_fields=[
                "email",
                "role",
                "is_staff",
                "is_active",
                "password",
            ]
        )

        instructor_permissions = Permission.objects.filter(
            content_type__app_label__in=("accounts", "academy"),
        ).exclude(
            codename__startswith="delete_",
        )

        user.user_permissions.set(instructor_permissions)

        action = "created" if created else "updated"

        self.stdout.write(
            self.style.SUCCESS(
                f"Deployment instructor account {action}: {username}"
            )
        )
