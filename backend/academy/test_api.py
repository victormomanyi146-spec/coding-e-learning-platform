from django.contrib.auth import get_user_model
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
    Notification,
    Quiz,
    QuizChoice,
    QuizQuestion,
    Submission,
)


User = get_user_model()


class AcademyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.student = User.objects.create_user(
            username="api_student",
            password="StrongPass123!",
            role="STUDENT",
        )

        self.instructor = User.objects.create_user(
            username="api_instructor",
            password="StrongPass123!",
            role="INSTRUCTOR",
        )

        self.instructor.is_staff = True
        self.instructor.save(update_fields=["is_staff"])

        self.course = Course.objects.create(
            title="API Test Python",
            description="API integration test course",
            instructor="API Instructor",
            duration="4 weeks",
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
            title="Introduction to Python",
            content="Learn Python fundamentals.",
            order=1,
        )

        self.coding_activity = Activity.objects.create(
            lesson=self.lesson,
            title="Python Introduction Exercise",
            activity_type="coding",
            instructions="Print a message.",
            order=1,
            max_score=20,
            is_required=True,
        )

        self.quiz_activity = Activity.objects.create(
            lesson=self.lesson,
            title="Python Fundamentals Quiz",
            activity_type="quiz",
            instructions="Answer the Python questions.",
            order=2,
            max_score=10,
            is_required=False,
        )

        self.quiz = Quiz.objects.create(
            activity=self.quiz_activity,
            passing_score=50,
        )

        self.question_1 = QuizQuestion.objects.create(
            quiz=self.quiz,
            question_text="Which function displays output in Python?",
            points=5,
            order=1,
            is_active=True,
        )

        self.question_2 = QuizQuestion.objects.create(
            quiz=self.quiz,
            question_text="Which symbol starts a Python comment?",
            points=5,
            order=2,
            is_active=True,
        )

        self.choice_1_correct = QuizChoice.objects.create(
            question=self.question_1,
            choice_text="print()",
            is_correct=True,
            order=1,
        )

        QuizChoice.objects.create(
            question=self.question_1,
            choice_text="input()",
            is_correct=False,
            order=2,
        )

        self.choice_2_correct = QuizChoice.objects.create(
            question=self.question_2,
            choice_text="#",
            is_correct=True,
            order=1,
        )

        QuizChoice.objects.create(
            question=self.question_2,
            choice_text="//",
            is_correct=False,
            order=2,
        )

    def authenticate_student(self):
        token, _ = Token.objects.get_or_create(
            user=self.student
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}"
        )
        return token

    def authenticate_instructor(self):
        token, _ = Token.objects.get_or_create(
            user=self.instructor
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}"
        )
        return token

    def test_course_list_api_is_public(self):
        response = self.client.get(
            "/api/courses/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            any(
                course["slug"] == self.course.slug
                for course in response.data["results"]
            )
        )

    def test_student_login_api_returns_token(self):
        response = self.client.post(
            "/api/accounts/login/",
            {
                "username": "api_student",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "token",
            response.data,
        )

        self.assertEqual(
            response.data["user"]["role"],
            "STUDENT",
        )

    def test_instructor_login_api_returns_token(self):
        response = self.client.post(
            "/api/accounts/instructor-login/",
            {
                "username": "api_instructor",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "token",
            response.data,
        )

        self.assertEqual(
            response.data["user"]["role"],
            "INSTRUCTOR",
        )

        self.assertTrue(
            response.data["user"]["is_staff"]
        )

    def test_student_can_enroll_and_read_progress(self):
        self.authenticate_student()

        enrollment_response = self.client.post(
            f"/api/courses/{self.course.slug}/enroll/"
        )

        self.assertIn(
            enrollment_response.status_code,
            [200, 201],
        )

        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course,
            ).exists()
        )

        progress_response = self.client.get(
            f"/api/courses/{self.course.slug}/progress/"
        )

        self.assertEqual(
            progress_response.status_code,
            200,
        )

        self.assertTrue(
            progress_response.data["is_enrolled"]
        )

        self.assertEqual(
            progress_response.data["progress"]["lessons_total"],
            1,
        )

    def test_student_can_submit_and_pass_quiz(self):
        self.authenticate_student()

        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        ActivityCompletion.objects.create(
            student=self.student,
            activity=self.coding_activity,
        )

        response = self.client.get(
            f"/api/quizzes/{self.quiz_activity.id}/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        attempt_response = self.client.post(
            f"/api/quizzes/{self.quiz_activity.id}/attempts/",
            {
                "answers": {
                    str(self.question_1.id): self.choice_1_correct.id,
                    str(self.question_2.id): self.choice_2_correct.id,
                }
            },
            format="json",
        )

        self.assertEqual(
            attempt_response.status_code,
            201,
        )

        self.assertEqual(
            attempt_response.data["result"]["earned_points"],
            10,
        )

        self.assertEqual(
            attempt_response.data["result"]["percentage"],
            100,
        )

        self.assertTrue(
            attempt_response.data["result"]["passed"]
        )

    def test_instructor_can_grade_submission_and_notify_student(self):
        self.authenticate_student()

        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        submission_response = self.client.post(
            "/api/submissions/",
            {
                "activity": self.coding_activity.id,
                "code": 'print("Hello from API tests")',
                "response_text": "",
                "github_url": "",
            },
            format="json",
        )

        self.assertIn(
            submission_response.status_code,
            [200, 201],
        )

        self.assertEqual(
            submission_response.status_code,
            201,
        )

        submission_id = submission_response.data["submission"]["id"]

        submission = Submission.objects.get(
            id=submission_id
        )

        self.assertEqual(
            submission.student,
            self.student,
        )

        self.authenticate_instructor()

        review_response = self.client.post(
            f"/api/submissions/{submission_id}/review/",
            {
                "score": 19,
                "feedback": "API regression test grading succeeded.",
                "status": "graded",
            },
            format="json",
        )

        self.assertEqual(
            review_response.status_code,
            200,
        )

        submission.refresh_from_db()

        self.assertEqual(
            submission.score,
            19,
        )

        self.assertEqual(
            submission.status,
            "graded",
        )

        self.assertEqual(
            submission.feedback,
            "API regression test grading succeeded.",
        )

        self.assertTrue(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=self.coding_activity,
            ).exists()
        )

        notification = Notification.objects.filter(
            recipient=self.student,
            notification_type="graded",
        ).latest("created_at")

        self.assertFalse(
            notification.is_read
        )

        self.assertIn(
            "API regression test grading succeeded.",
            notification.message,
        )

        self.authenticate_student()

        notifications_response = self.client.get(
            "/api/notifications/"
        )

        self.assertEqual(
            notifications_response.status_code,
            200,
        )

        self.assertGreaterEqual(
            notifications_response.data["unread_count"],
            1,
        )

        read_response = self.client.post(
            f"/api/notifications/{notification.id}/read/"
        )

        self.assertEqual(
            read_response.status_code,
            200,
        )

        notification.refresh_from_db()

        self.assertTrue(
            notification.is_read
        )

        unread_response = self.client.get(
            "/api/notifications/unread/"
        )

        self.assertEqual(
            unread_response.status_code,
            200,
        )

        unread_ids = [
            item["id"]
            for item in unread_response.data["results"]
        ]

        self.assertNotIn(
            notification.id,
            unread_ids,
        )
