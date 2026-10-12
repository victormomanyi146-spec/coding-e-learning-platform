from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import FileExtensionValidator

from .models import InstructorApplication, User, validate_instructor_upload_size
from rest_framework import serializers


class StudentLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        user = authenticate(
            username=username,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError(
                "Invalid username or password."
            )

        if user.role != User.Roles.STUDENT or user.is_staff or user.is_superuser:
            raise serializers.ValidationError(
                "This login is for students only."
            )

        # Applicants do not receive student access while their instructor application is pending or rejected.
        if hasattr(user, "instructor_application"):
            raise serializers.ValidationError(
                "This account has an instructor application and cannot use student sign-in. Check your application status."
            )

        data["user"] = user
        return data

class InstructorLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        user = authenticate(
            username=username,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError(
                "Invalid username or password."
            )

        if user.role != User.Roles.INSTRUCTOR or user.is_superuser:
            raise serializers.ValidationError(
                "This login is for instructors only."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This instructor account is inactive."
            )

        data["user"] = user
        return data


class StudentRegistrationSerializer(serializers.Serializer):
    """Validate and create student accounts without accepting privileged roles."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with that username already exists."
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with that email address already exists."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })

        try:
            validate_password(attrs["password"])
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "password": list(error.messages)
            }) from error

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        # Never accept a role from the registration request.
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=password,
            role=User.Roles.STUDENT,
        )


class AdminLoginSerializer(serializers.Serializer):
    """Authenticate only active Django superusers as platform administrators."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            username=data.get("username"),
            password=data.get("password"),
        )

        if user is None or not user.is_active or not user.is_superuser:
            raise serializers.ValidationError(
                "Invalid administrator credentials."
            )

        data["user"] = user
        return data


class InstructorApplicationCreateSerializer(serializers.Serializer):
    """Validate a public instructor application without granting instructor privileges."""

    username = serializers.CharField(max_length=150, min_length=3, validators=[UnicodeUsernameValidator()])
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    qualification = serializers.CharField(max_length=200, trim_whitespace=True)
    awarding_institution = serializers.CharField(max_length=200, trim_whitespace=True)
    experience_summary = serializers.CharField(max_length=3000, trim_whitespace=True)
    cv = serializers.FileField(validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx"]), validate_instructor_upload_size])
    qualification_document = serializers.FileField(
        required=False,
        allow_null=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "png", "jpg", "jpeg"]), validate_instructor_upload_size],
    )

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with that email address already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        for field in ("qualification", "awarding_institution", "experience_summary"):
            if not attrs[field].strip():
                raise serializers.ValidationError({field: "This field cannot be blank."})
        return attrs
