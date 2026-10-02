from rest_framework import serializers

from .models import (
    Activity,
    Course,
    Lesson,
    Module,
    Submission,
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


class SubmissionAPISerializer(serializers.ModelSerializer):
    """Read-only representation of a submission."""

    student = serializers.SerializerMethodField()
    activity = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id",
            "student",
            "activity",
            "course",
            "code",
            "response_text",
            "github_url",
            "attachment_url",
            "submitted_at",
            "status",
            "score",
            "feedback",
        ]
        read_only_fields = fields

    def get_student(self, obj):
        return {
            "id": obj.student_id,
            "username": obj.student.username,
        }

    def get_activity(self, obj):
        return {
            "id": obj.activity_id,
            "title": obj.activity.title,
            "activity_type": obj.activity.activity_type,
            "max_score": obj.activity.max_score,
        }

    def get_course(self, obj):
        course = obj.activity.lesson.course

        return {
            "id": course.id,
            "title": course.title,
            "slug": course.slug,
        }

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None

        try:
            url = obj.attachment.url
        except (AttributeError, ValueError):
            return None

        request = self.context.get("request")

        if request is not None:
            return request.build_absolute_uri(url)

        return url
