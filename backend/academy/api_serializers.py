from rest_framework import serializers

from .models import (
    Activity,
    Course,
    Lesson,
    Module,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizChoice,
    QuizQuestion,
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


class QuizChoiceAPISerializer(serializers.ModelSerializer):
    """Public quiz choice representation; correct answers are hidden."""

    class Meta:
        model = QuizChoice
        fields = [
            "id",
            "choice_text",
            "order",
        ]
        read_only_fields = fields


class QuizQuestionAPISerializer(serializers.ModelSerializer):
    choices = QuizChoiceAPISerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = QuizQuestion
        fields = [
            "id",
            "question_text",
            "order",
            "points",
            "choices",
        ]
        read_only_fields = fields


class QuizAPISerializer(serializers.ModelSerializer):
    activity = serializers.SerializerMethodField()
    questions = QuizQuestionAPISerializer(
        many=True,
        read_only=True,
    )
    total_points = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "activity",
            "passing_score",
            "total_points",
            "questions",
            "created_at",
        ]
        read_only_fields = fields

    def get_activity(self, obj):
        activity = obj.activity
        lesson = activity.lesson
        course = lesson.course

        return {
            "id": activity.id,
            "title": activity.title,
            "activity_type": activity.activity_type,
            "instructions": activity.instructions,
            "max_score": activity.max_score,
            "lesson": {
                "id": lesson.id,
                "title": lesson.title,
            },
            "course": {
                "id": course.id,
                "title": course.title,
                "slug": course.slug,
            },
        }

    def get_total_points(self, obj):
        return sum(
            question.points
            for question in obj.questions.filter(
                is_active=True,
            )
        )


class QuizAnswerAPISerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()
    selected_choice = serializers.SerializerMethodField()

    class Meta:
        model = QuizAnswer
        fields = [
            "id",
            "question",
            "selected_choice",
            "is_correct",
            "points_awarded",
        ]
        read_only_fields = fields

    def get_question(self, obj):
        return {
            "id": obj.question_id,
            "question_text": obj.question.question_text,
            "points": obj.question.points,
        }

    def get_selected_choice(self, obj):
        if obj.selected_choice is None:
            return None

        return {
            "id": obj.selected_choice_id,
            "choice_text": obj.selected_choice.choice_text,
        }


class QuizAttemptAPISerializer(serializers.ModelSerializer):
    quiz = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()
    answers = QuizAnswerAPISerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "quiz",
            "score",
            "total_points",
            "percentage",
            "passed",
            "completed_at",
            "created_at",
            "answers",
        ]
        read_only_fields = fields

    def get_quiz(self, obj):
        quiz = obj.quiz
        activity = quiz.activity
        lesson = activity.lesson
        course = lesson.course

        return {
            "id": quiz.id,
            "activity_id": activity.id,
            "title": activity.title,
            "passing_score": quiz.passing_score,
            "lesson": {
                "id": lesson.id,
                "title": lesson.title,
            },
            "course": {
                "id": course.id,
                "title": course.title,
                "slug": course.slug,
            },
        }

    def get_total_points(self, obj):
        return sum(
            question.points
            for question in obj.quiz.questions.filter(
                is_active=True,
            )
        )

    def get_percentage(self, obj):
        total_points = self.get_total_points(obj)

        if not total_points:
            return 0

        return round(
            (obj.score / total_points) * 100
        )
