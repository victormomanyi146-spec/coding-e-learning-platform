from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import (
    Activity,
    ActivityCompletion,
    Course,
    Enrollment,
    Lesson,
    Module,
    Submission,
)


User = get_user_model()


class CourseProgressAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.student = User.objects.create_user(
            username="progress_api_student",
            password="testpass123",
        )

        self.other_student = User.objects.create_user(
            username="other_progress_student",
            password="testpass123",
        )

        self.instructor = User.objects.create_user(
            username="progress_api_instructor",
            password="testpass123",
        )

        self.course = Course.objects.create(
            title="Progress API Course",
            slug="progress-api-course",
            description="Course progress API test course.",
            instructor=self.instructor,
            duration="4 weeks",
            level="Beginner",
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Module 1",
            order=1,
        )

        self.lesson_one = Lesson.objects.create(
            course=self.course,
            module=self.module,
            title="Lesson 1",
            order=1,
        )

        self.lesson_two = Lesson.objects.create(
            course=self.course,
            module=self.module,
            title="Lesson 2",
            order=2,
        )

        self.activity_one = Activity.objects.create(
            lesson=self.lesson_one,
            title="First coding activity",
            activity_type="coding",
            instructions="Print Hello.",
            order=1,
            max_score=20,
            is_required=True,
        )

        self.activity_two = Activity.objects.create(
            lesson=self.lesson_two,
            title="Second coding activity",
            activity_type="coding",
            instructions="Print World.",
            order=1,
            max_score=20,
            is_required=True,
        )

        self.token = Token.objects.create(
            user=self.student,
        )

        self.url = reverse(
            "api-course-progress",
            args=[self.course.slug],
        )

    def authenticate(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}",
        )

    def test_progress_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_progress_requires_enrollment(self):
        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            response.data["is_enrolled"],
        )

    def test_progress_returns_authenticated_student_data(self):
        self.authenticate()

        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        ActivityCompletion.objects.create(
            student=self.student,
            activity=self.activity_one,
        )

        Submission.objects.create(
            student=self.student,
            activity=self.activity_one,
            code='print("Hello")',
            score=18,
            status="graded",
            feedback="Good work.",
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["is_enrolled"],
        )

        self.assertEqual(
            response.data["progress"]["lessons_total"],
            2,
        )

        self.assertEqual(
            response.data["progress"]["lessons_completed"],
            1,
        )

        self.assertEqual(
            response.data["progress"]["activities_total"],
            2,
        )

        self.assertEqual(
            response.data["progress"]["activities_completed"],
            1,
        )

        self.assertEqual(
            response.data["progress"]["overall_percentage"],
            50,
        )

        self.assertEqual(
            response.data["progress"]["activity_percentage"],
            50,
        )

        self.assertEqual(
            response.data["progress"]["average_score"],
            90.0,
        )

        self.assertEqual(
            len(response.data["modules"]),
            1,
        )

        self.assertEqual(
            response.data["modules"][0]["progress_percentage"],
            50,
        )

        self.assertEqual(
            len(response.data["modules"][0]["lessons"]),
            2,
        )

        self.assertTrue(
            response.data["modules"][0]["lessons"][0]["is_completed"],
        )

        self.assertFalse(
            response.data["modules"][0]["lessons"][1]["is_completed"],
        )

        self.assertEqual(
            len(response.data["recent_assessments"]),
            1,
        )

        self.assertEqual(
            response.data["recent_assessments"][0]["title"],
            "First coding activity",
        )

        self.assertEqual(
            response.data["recent_assessments"][0]["status"],
            "Graded",
        )

    def test_progress_is_scoped_to_authenticated_user(self):
        Enrollment.objects.create(
            student=self.other_student,
            course=self.course,
        )

        other_token = Token.objects.create(
            user=self.other_student,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {other_token.key}",
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["progress"]["activities_completed"],
            0,
        )

        self.assertIsNone(
            response.data["progress"]["average_score"],
        )

    def test_unknown_course_returns_404(self):
        self.authenticate()

        response = self.client.get(
            reverse(
                "api-course-progress",
                args=["does-not-exist"],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_error_submission_is_reported_as_error(self):
        self.authenticate()

        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        Submission.objects.create(
            student=self.student,
            activity=self.activity_one,
            code='print("broken")',
            status="error",
            feedback="Execution failed.",
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["recent_assessments"][0]["status"],
            "Error",
        )
