from rest_framework import serializers

from .models import (
    Activity,
    Course,
    Lesson,
    Module,
)


class ActivityAPISerializer(serializers.ModelSerializer):

    class Meta:
        model = Activity
        fields = [
            "id",
            "title",
            "activity_type",
            "instructions",
            "order",
            "max_score",
            "is_required",
        ]


class LessonAPISerializer(serializers.ModelSerializer):

    activities = ActivityAPISerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "content",
            "order",
            "activities",
        ]


class ModuleAPISerializer(serializers.ModelSerializer):

    lessons = LessonAPISerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Module
        fields = [
            "id",
            "title",
            "order",
            "lessons",
        ]


class CourseListAPISerializer(serializers.ModelSerializer):

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "instructor",
            "duration",
            "level",
            "created_at",
        ]


class CourseDetailAPISerializer(serializers.ModelSerializer):

    modules = ModuleAPISerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "instructor",
            "duration",
            "level",
            "created_at",
            "modules",
        ]
