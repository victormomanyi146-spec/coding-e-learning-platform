from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Activity,
    ActivityCompletion,
    Course,
    Lesson,
    Module,
    Submission,
)


User = get_user_model()


class AcademyFlowTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student",
            password="StrongPass123!",
            role="STUDENT",
        )
        self.instructor = User.objects.create_user(
            username="instructor",
            password="StrongPass123!",
            role="INSTRUCTOR",
        )
        self.course = Course.objects.create(
            title="Test Python",
            description="Test course",
            instructor="Instructor",
            duration="4 weeks",
            level="Beginner",
        )
        self.module = Module.objects.create(
            course=self.course,
            title="Fundamentals",
            order=1,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            module=self.module,
            title="Input",
            content="Learn input.",
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

    def test_course_detail_loads_modules(self):
        response = self.client.get(
            reverse("course_detail", args=[self.course.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fundamentals")

    def test_course_progress_displays_real_values(self):
        self.client.force_login(self.student)
        ActivityCompletion.objects.create(
            student=self.student,
            activity=self.activity,
        )

        response = self.client.get(
            reverse("course_progress", args=[self.course.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "100%")
        self.assertContains(response, "1 / 1 lessons completed")

    def test_activity_page_renders_code_and_program_input_fields(self):
        response = self.client.get(
            reverse(
                "activity_detail",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="code-editor"')
        self.assertContains(response, 'name="program_input"')

    def test_student_submission_creates_completion(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse(
                "activity_detail",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                "code": 'print("Hello")',
                "program_input": "",
                "submit_activity": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Submission.objects.filter(
                student=self.student,
                activity=self.activity,
            ).exists()
        )
        self.assertTrue(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=self.activity,
            ).exists()
        )

    def test_submission_history_redirects_unauthenticated_users(self):
        url = reverse(
            "submission_history",
            args=[
                self.course.slug,
                self.lesson.id,
                self.activity.id,
            ],
        )

        self.assertEqual(self.client.get(url).status_code, 302)

        self.client.force_login(self.student)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_instructor_can_review_submission(self):
        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Hello")',
        )

        self.client.force_login(self.instructor)

        response = self.client.post(
            reverse("review_submission", args=[submission.id]),
            {
                "score": "18",
                "feedback": "Good work.",
            },
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.score, 18)
        self.assertEqual(submission.status, "graded")
        self.assertEqual(submission.feedback, "Good work.")

    def test_student_cannot_access_instructor_submissions(self):
        self.client.force_login(self.student)
        response = self.client.get(
            reverse("instructor_submissions")
        )
        self.assertEqual(response.status_code, 403)
