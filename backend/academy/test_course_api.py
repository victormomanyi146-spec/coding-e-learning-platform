from django.test import TestCase

from rest_framework.test import APIClient

from .models import (
    Activity,
    Course,
    Lesson,
    Module,
)


class CourseAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.course = Course.objects.create(
            title="API Python Course",
            description="Python API course",
            instructor="Instructor",
            duration="8 weeks",
            level="Beginner",
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Python Fundamentals",
            order=1,
        )

        self.lesson = Lesson.objects.create(
            course=self.course,
            module=self.module,
            title="Input and Output",
            content="Learn Python input and output.",
            order=1,
        )

        self.activity = Activity.objects.create(
            lesson=self.lesson,
            title="Input Exercise",
            activity_type="coding",
            instructions="Use input().",
            order=1,
            max_score=20,
            is_required=True,
        )

    def test_course_list_api_returns_courses(self):
        response = self.client.get("/api/courses/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["title"],
            "API Python Course",
        )

    def test_course_list_api_is_public(self):
        response = self.client.get("/api/courses/")

        self.assertEqual(response.status_code, 200)

    def test_course_detail_api_returns_nested_learning_content(self):
        response = self.client.get(
            f"/api/courses/{self.course.slug}/",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], self.course.slug)
        self.assertEqual(len(response.data["modules"]), 1)

        module = response.data["modules"][0]

        self.assertEqual(
            module["title"],
            "Python Fundamentals",
        )

        self.assertEqual(len(module["lessons"]), 1)

        lesson = module["lessons"][0]

        self.assertEqual(
            lesson["title"],
            "Input and Output",
        )

        self.assertEqual(len(lesson["activities"]), 1)

        activity = lesson["activities"][0]

        self.assertEqual(
            activity["title"],
            "Input Exercise",
        )

    def test_course_detail_api_returns_activity_metadata(self):
        response = self.client.get(
            f"/api/courses/{self.course.slug}/",
        )

        self.assertEqual(response.status_code, 200)

        activity = (
            response.data["modules"][0]
            ["lessons"][0]
            ["activities"][0]
        )

        self.assertEqual(
            activity["activity_type"],
            "coding",
        )

        self.assertEqual(
            activity["max_score"],
            20,
        )

        self.assertTrue(
            activity["is_required"],
        )

    def test_unknown_course_returns_404(self):
        response = self.client.get(
            "/api/courses/does-not-exist/",
        )

        self.assertEqual(response.status_code, 404)
