from django.contrib.auth import authenticate

from .models import User
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

        if user.role != User.Roles.STUDENT:
            raise serializers.ValidationError(
                "This login is for students only."
            )

        data["user"] = user
        return data