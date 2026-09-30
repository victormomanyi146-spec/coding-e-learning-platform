from academy.models import (
    Quiz,
    QuizQuestion,
    QuizChoice,
    QuizAttempt,
)
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Activity,
    ActivityCompletion,
    Course,
    Enrollment,
    Lesson,
    Module,
    Submission,
    Notification,
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


    


    def enroll_student(self):
        return Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
    def test_course_detail_loads_modules(self):
        response = self.client.get(
            reverse(
                "course_detail",
                args=[self.course.slug],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Fundamentals",
        )

    def test_course_progress_displays_real_values(self):
        self.enroll_student()
        self.client.force_login(
            self.student
        )

        ActivityCompletion.objects.create(
            student=self.student,
            activity=self.activity,
        )

        response = self.client.get(
            reverse(
                "course_progress",
                args=[self.course.slug],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "100%",
        )

        self.assertContains(
            response,
            "<strong>1</strong>",
            html=True,
        )

        self.assertContains(
            response,
            "/ 1 lessons completed",
        )

    def test_activity_page_renders_code_and_program_input_fields(self):
        self.enroll_student()
        self.client.force_login(self.student)

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

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            'id="code-editor"',
        )

        self.assertContains(
            response,
            'name="program_input"',
        )

    @override_settings(DEBUG=True)
    def test_student_submission_creates_completion(self):
        self.enroll_student()
        self.client.force_login(
            self.student
        )

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

        self.assertEqual(
            response.status_code,
            200,
        )

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

        self.assertEqual(
            self.client.get(url).status_code,
            302,
        )

        self.client.force_login(
            self.student
        )

        self.assertEqual(
            self.client.get(url).status_code,
            200,
        )

    def test_instructor_can_review_submission(self):
        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Hello")',
        )

        self.client.force_login(
            self.instructor
        )

        response = self.client.post(
            reverse(
                "review_submission",
                args=[submission.id],
            ),
            {
                "score": "18",
                "feedback": "Good work.",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        submission.refresh_from_db()

        self.assertEqual(
            submission.score,
            18,
        )

        self.assertEqual(
            submission.status,
            "graded",
        )

        self.assertEqual(
            submission.feedback,
            "Good work.",
        )

    def test_instructor_can_mark_submission_for_correction(self):
        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Needs fixing")',
        )

        ActivityCompletion.objects.create(
            student=self.student,
            activity=self.activity,
        )

        self.client.force_login(
            self.instructor
        )

        response = self.client.post(
            reverse(
                "review_submission",
                args=[submission.id],
            ),
            {
                "score": "0",
                "feedback": "Needs correction.",
                "status": "correction",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        submission.refresh_from_db()

        self.assertEqual(
            submission.status,
            "correction",
        )

        self.assertEqual(
            submission.score,
            0,
        )

        self.assertEqual(
            submission.feedback,
            "Needs correction.",
        )

        self.assertFalse(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=self.activity,
            ).exists()
        )


    def test_instructor_can_restore_completion_after_correction(self):
        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Fix")',
            status="correction",
            score=0,
            feedback="Please correct the input handling.",
        )

        self.client.force_login(
            self.instructor
        )

        correction_response = self.client.post(
            reverse(
                "review_submission",
                args=[submission.id],
            ),
            {
                "score": "0",
                "feedback": "Please correct the input handling.",
                "status": "correction",
            },
        )

        self.assertEqual(
            correction_response.status_code,
            302,
        )

        self.assertFalse(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=self.activity,
            ).exists()
        )

        graded_response = self.client.post(
            reverse(
                "review_submission",
                args=[submission.id],
            ),
            {
                "score": "18",
                "feedback": "Corrected and graded.",
                "status": "graded",
            },
        )

        self.assertEqual(
            graded_response.status_code,
            302,
        )

        submission.refresh_from_db()

        self.assertEqual(
            submission.status,
            "graded",
        )

        self.assertEqual(
            submission.score,
            18,
        )

        self.assertTrue(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=self.activity,
            ).exists()
        )


    def test_student_activity_displays_correction_feedback(self):
        self.enroll_student()

        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Needs fixing")',
            status="correction",
            score=0,
            feedback="Please correct the age conversion.",
        )

        self.client.force_login(
            self.student
        )

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

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Submission needs correction",
        )

        self.assertContains(
            response,
            "Please correct the age conversion.",
        )

        self.assertContains(
            response,
            "Correction required.",
        )

        self.assertNotContains(
            response,
            "Your progress has been recorded.",
        )


    def test_student_assessment_history_marks_correction_submission(self):
        self.enroll_student()

        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Needs fixing")',
            status="correction",
            score=0,
            feedback="Please correct the age conversion.",
        )

        self.client.force_login(
            self.student
        )

        response = self.client.get(
            reverse(
                "student_assessment_history",
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Needs Correction",
        )

        self.assertContains(
            response,
            "Correct &amp; Resubmit",
            html=True,
        )

        correction_response = self.client.get(
            reverse(
                "student_assessment_history",
            )
            + "?status=correction"
        )

        self.assertEqual(
            correction_response.status_code,
            200,
        )

        self.assertContains(
            correction_response,
            "Please correct the age conversion.",
        )


    def test_instructor_grading_creates_student_notification(self):
        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Hello")',
        )

        self.client.force_login(
            self.instructor
        )

        response = self.client.post(
            reverse(
                "review_submission",
                args=[submission.id],
            ),
            {
                "score": "18",
                "feedback": "Good work.",
                "status": "graded",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        notification = Notification.objects.get(
            recipient=self.student,
        )

        self.assertEqual(
            notification.notification_type,
            "graded",
        )

        self.assertEqual(
            notification.title,
            "Submission Graded",
        )

        self.assertIn(
            self.activity.title,
            notification.message,
        )

        self.assertIn(
            "Good work.",
            notification.message,
        )

        self.assertFalse(
            notification.is_read,
        )

        expected_url = reverse(
            "activity_detail",
            args=[
                self.course.slug,
                self.lesson.id,
                self.activity.id,
            ],
        )

        self.assertEqual(
            notification.link_url,
            expected_url,
        )


    def test_correction_assessment_creates_correction_notification(self):
        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Needs fixing")',
        )

        self.client.force_login(
            self.instructor
        )

        response = self.client.post(
            reverse(
                "review_submission",
                args=[submission.id],
            ),
            {
                "score": "0",
                "feedback": "Please correct the input handling.",
                "status": "correction",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        notification = Notification.objects.get(
            recipient=self.student,
        )

        self.assertEqual(
            notification.notification_type,
            "correction",
        )

        self.assertEqual(
            notification.title,
            "Correction Required",
        )

        self.assertIn(
            "Please correct the input handling.",
            notification.message,
        )

        self.assertFalse(
            notification.is_read,
        )


    def test_student_notification_read_marks_notification_and_redirects(self):
        self.enroll_student()

        notification = Notification.objects.create(
            recipient=self.student,
            notification_type="graded",
            title="Submission Graded",
            message="Your submission has been graded.",
            link_url=reverse(
                "activity_detail",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
        )

        self.client.force_login(
            self.student
        )

        response = self.client.get(
            reverse(
                "notification_read",
                args=[notification.id],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        notification.refresh_from_db()

        self.assertTrue(
            notification.is_read,
        )

        self.assertEqual(
            response.url,
            notification.link_url,
        )


    def test_student_cannot_read_another_users_notification(self):
        other_student = User.objects.create_user(
            username="other_notification_student",
            password="StrongPass123!",
            role="STUDENT",
        )

        notification = Notification.objects.create(
            recipient=other_student,
            notification_type="graded",
            title="Private Notification",
            message="Private message.",
        )

        self.client.force_login(
            self.student
        )

        response = self.client.get(
            reverse(
                "notification_read",
                args=[notification.id],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )


    def test_notification_list_shows_only_current_students_notifications(self):
        other_student = User.objects.create_user(
            username="other_notification_user",
            password="StrongPass123!",
            role="STUDENT",
        )

        Notification.objects.create(
            recipient=self.student,
            notification_type="graded",
            title="My Notification",
            message="This belongs to me.",
        )

        Notification.objects.create(
            recipient=other_student,
            notification_type="graded",
            title="Other Notification",
            message="This belongs to another student.",
        )

        self.client.force_login(
            self.student
        )

        response = self.client.get(
            reverse("notification_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "My Notification",
        )

        self.assertNotContains(
            response,
            "Other Notification",
        )


    def test_notification_unread_count_appears_in_shared_navigation(self):
        Notification.objects.create(
            recipient=self.student,
            notification_type="graded",
            title="First Notification",
            message="First update.",
            is_read=False,
        )

        Notification.objects.create(
            recipient=self.student,
            notification_type="correction",
            title="Second Notification",
            message="Second update.",
            is_read=False,
        )

        Notification.objects.create(
            recipient=self.student,
            notification_type="graded",
            title="Read Notification",
            message="Already read.",
            is_read=True,
        )

        self.client.force_login(
            self.student
        )

        response = self.client.get(
            reverse("notification_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Notifications",
        )

        self.assertContains(
            response,
            "(2)",
        )


    def test_reading_notification_removes_it_from_unread_count(self):
        notification = Notification.objects.create(
            recipient=self.student,
            notification_type="graded",
            title="Unread Update",
            message="Please review your grade.",
            link_url=reverse(
                "activity_detail",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            is_read=False,
        )

        self.client.force_login(
            self.student
        )

        before_response = self.client.get(
            reverse("notification_list")
        )

        self.assertContains(
            before_response,
            "(1)",
        )

        response = self.client.get(
            reverse(
                "notification_read",
                args=[notification.id],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        after_response = self.client.get(
            reverse("notification_list")
        )

        self.assertNotContains(
            after_response,
            "(1)",
        )

        notification.refresh_from_db()

        self.assertTrue(
            notification.is_read,
        )


    def test_student_cannot_access_instructor_submissions(self):
        self.client.force_login(
            self.student
        )

        response = self.client.get(
            reverse(
                "instructor_submissions"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )


    def test_first_lesson_is_accessible(self):
        self.enroll_student()
        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "lesson_detail",
                args=[
                    self.course.slug,
                    self.lesson.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Input")

    def test_incomplete_lesson_blocks_next_lesson(self):
        self.enroll_student()
        second_lesson = Lesson.objects.create(
            course=self.course,
            module=self.module,
            title="Variables",
            content="Learn variables.",
            order=2,
        )

        Activity.objects.create(
            lesson=second_lesson,
            title="Variables Exercise",
            activity_type="coding",
            instructions="Practice variables.",
            order=1,
            max_score=20,
            is_required=True,
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "lesson_detail",
                args=[
                    self.course.slug,
                    second_lesson.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "locked",
            status_code=403,
        )

    def test_completed_lesson_unlocks_next_lesson(self):
        self.enroll_student()
        second_lesson = Lesson.objects.create(
            course=self.course,
            module=self.module,
            title="Variables",
            content="Learn variables.",
            order=2,
        )

        Activity.objects.create(
            lesson=second_lesson,
            title="Variables Exercise",
            activity_type="coding",
            instructions="Practice variables.",
            order=1,
            max_score=20,
            is_required=True,
        )

        ActivityCompletion.objects.create(
            student=self.student,
            activity=self.activity,
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "lesson_detail",
                args=[
                    self.course.slug,
                    second_lesson.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Variables")

    def test_optional_activity_does_not_block_progression(self):
        self.enroll_student()
        optional_activity = Activity.objects.create(
            lesson=self.lesson,
            title="Optional Practice",
            activity_type="coding",
            instructions="Optional practice.",
            order=2,
            max_score=20,
            is_required=False,
        )

        ActivityCompletion.objects.create(
            student=self.student,
            activity=self.activity,
        )

        second_lesson = Lesson.objects.create(
            course=self.course,
            module=self.module,
            title="Variables",
            content="Learn variables.",
            order=2,
        )

        Activity.objects.create(
            lesson=second_lesson,
            title="Variables Exercise",
            activity_type="coding",
            instructions="Practice variables.",
            order=1,
            max_score=20,
            is_required=True,
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "lesson_detail",
                args=[
                    self.course.slug,
                    second_lesson.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_previous_module_blocks_next_module(self):
        second_module = Module.objects.create(
            course=self.course,
            title="Intermediate",
            order=2,
        )

        second_lesson = Lesson.objects.create(
            course=self.course,
            module=second_module,
            title="Functions",
            content="Learn functions.",
            order=1,
        )

        Activity.objects.create(
            lesson=second_lesson,
            title="Functions Exercise",
            activity_type="coding",
            instructions="Practice functions.",
            order=1,
            max_score=20,
            is_required=True,
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "lesson_detail",
                args=[
                    self.course.slug,
                    second_lesson.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_direct_activity_url_cannot_bypass_locked_lesson(self):
        second_lesson = Lesson.objects.create(
            course=self.course,
            module=self.module,
            title="Variables",
            content="Learn variables.",
            order=2,
        )

        second_activity = Activity.objects.create(
            lesson=second_lesson,
            title="Variables Exercise",
            activity_type="coding",
            instructions="Practice variables.",
            order=1,
            max_score=20,
            is_required=True,
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "activity_detail",
                args=[
                    self.course.slug,
                    second_lesson.id,
                    second_activity.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 403)


    def test_student_can_enroll_in_course(self):
        course = Course.objects.create(
            title="Django Test",
            description="Test Django course",
            instructor="Instructor",
            duration="6 weeks",
            level="Intermediate",
        )

        self.client.force_login(self.student)

        response = self.client.post(
            reverse(
                "enroll_course",
                args=[course.slug],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student,
                course=course,
            ).exists()
        )
    def test_duplicate_enrollment_does_not_create_second_record(self):

        self.client.force_login(self.student)

        response = self.client.post(
            reverse(
                "enroll_course",
                args=[self.course.slug],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course,
            ).count(),
            1,
        )

    def test_unauthenticated_user_cannot_enroll(self):
        response = self.client.post(
            reverse(
                "enroll_course",
                args=[self.course.slug],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            Enrollment.objects.filter(
                course=self.course,
            ).exists()
        )

    def test_my_courses_displays_enrolled_course(self):
        self.enroll_student()

        self.client.force_login(self.student)

        response = self.client.get(
            reverse("my_courses")
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            self.course.title,
        )

    def create_quiz(self):

        quiz = Quiz.objects.create(
            activity=self.activity,
            passing_score=50,
        )

        question_one = QuizQuestion.objects.create(
            quiz=quiz,
            question_text="What is Python?",
            order=1,
            points=10,
            is_active=True,
        )

        QuizChoice.objects.create(
            question=question_one,
            choice_text="A programming language",
            is_correct=True,
            order=1,
        )

        QuizChoice.objects.create(
            question=question_one,
            choice_text="A database",
            is_correct=False,
            order=2,
        )

        question_two = QuizQuestion.objects.create(
            quiz=quiz,
            question_text="Which symbol starts a comment?",
            order=2,
            points=10,
            is_active=True,
        )

        QuizChoice.objects.create(
            question=question_two,
            choice_text="#",
            is_correct=True,
            order=1,
        )

        QuizChoice.objects.create(
            question=question_two,
            choice_text="//",
            is_correct=False,
            order=2,
        )

        return (
            quiz,
            question_one,
            question_two,
        )


    def test_quiz_page_requires_login(self):

        self.activity.activity_type = "quiz"
        self.activity.save()

        Quiz.objects.create(
            activity=self.activity,
            passing_score=50,
        )

        response = self.client.get(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )


    def test_quiz_page_requires_enrollment(self):

        self.activity.activity_type = "quiz"
        self.activity.save()

        Quiz.objects.create(
            activity=self.activity,
            passing_score=50,
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_quiz_can_be_submitted_and_passed(self):
        self.enroll_student()

        self.activity.activity_type = "quiz"
        self.activity.save()

        (
            quiz,
            question_one,
            question_two,
        ) = self.create_quiz()

        self.client.force_login(
            self.student
        )

        correct_one = (
            question_one.choices
            .get(is_correct=True)
        )

        correct_two = (
            question_two.choices
            .get(is_correct=True)
        )

        response = self.client.post(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                f"question_{question_one.id}":
                    str(correct_one.id),

                f"question_{question_two.id}":
                    str(correct_two.id),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        attempt = (
            QuizAttempt.objects
            .filter(
                quiz=quiz,
                student=self.student,
            )
            .latest("created_at")
        )

        self.assertEqual(
            attempt.score,
            20,
        )

        self.assertTrue(
            attempt.passed
        )

        self.assertTrue(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=self.activity,
            ).exists()
        )


    def test_quiz_failed_attempt_does_not_complete_activity(self):
        self.enroll_student()

        self.activity.activity_type = "quiz"
        self.activity.save()

        (
            quiz,
            question_one,
            question_two,
        ) = self.create_quiz()

        self.client.force_login(
            self.student
        )

        wrong_one = (
            question_one.choices
            .get(is_correct=False)
        )

        wrong_two = (
            question_two.choices
            .get(is_correct=False)
        )

        response = self.client.post(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                f"question_{question_one.id}":
                    str(wrong_one.id),

                f"question_{question_two.id}":
                    str(wrong_two.id),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        attempt = (
            QuizAttempt.objects
            .filter(
                quiz=quiz,
                student=self.student,
            )
            .latest("created_at")
        )

        self.assertEqual(
            attempt.score,
            0,
        )

        self.assertFalse(
            attempt.passed
        )

        self.assertFalse(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=self.activity,
            ).exists()
        )

    def test_course_progress_includes_quiz_attempt(self):
        self.enroll_student()

        self.activity.activity_type = "quiz"
        self.activity.save(update_fields=["activity_type"])

        (
            quiz,
            question_one,
            question_two,
        ) = self.create_quiz()

        self.client.force_login(self.student)

        correct_one = (
            question_one.choices
            .get(is_correct=True)
        )

        correct_two = (
            question_two.choices
            .get(is_correct=True)
        )

        response = self.client.post(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                f"question_{question_one.id}": str(correct_one.id),
                f"question_{question_two.id}": str(correct_two.id),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        progress_response = self.client.get(
            reverse(
                "course_progress",
                args=[self.course.slug],
            )
        )

        self.assertEqual(
            progress_response.status_code,
            200,
        )

        self.assertContains(
            progress_response,
            self.activity.title,
        )

        self.assertContains(
            progress_response,
            "Quiz Passed",
        )

        self.assertContains(
            progress_response,
            "100.0%",
        )

        self.assertContains(
            progress_response,
            "100.0%",
        )

    def test_quiz_history_displays_all_attempts(self):
        self.enroll_student()

        self.activity.activity_type = "quiz"
        self.activity.save(update_fields=["activity_type"])

        (
            quiz,
            question_one,
            question_two,
        ) = self.create_quiz()

        self.client.force_login(self.student)

        correct_one = (
            question_one.choices
            .get(is_correct=True)
        )

        correct_two = (
            question_two.choices
            .get(is_correct=True)
        )

        wrong_one = (
            question_one.choices
            .get(is_correct=False)
        )

        wrong_two = (
            question_two.choices
            .get(is_correct=False)
        )

        # First attempt: pass.
        response = self.client.post(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                f"question_{question_one.id}": str(correct_one.id),
                f"question_{question_two.id}": str(correct_two.id),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        # Second attempt: fail.
        response = self.client.post(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                f"question_{question_one.id}": str(wrong_one.id),
                f"question_{question_two.id}": str(wrong_two.id),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        history_response = self.client.get(
            reverse(
                "quiz_history",
                args=[self.course.slug],
            )
        )

        self.assertEqual(
            history_response.status_code,
            200,
        )

        self.assertContains(
            history_response,
            self.activity.title,
            count=2,
        )

        self.assertContains(
            history_response,
            "100.0%",
        )

        self.assertContains(
            history_response,
            "0.0%",
        )

        self.assertContains(
            history_response,
            "Quiz Passed",
        )

        self.assertContains(
            history_response,
            "Not passed",
        )

        self.assertEqual(
            QuizAttempt.objects.filter(
                quiz=quiz,
                student=self.student,
            ).count(),
            2,
        )

    def test_quiz_attempt_review_displays_answers(self):
        self.enroll_student()

        self.activity.activity_type = "quiz"
        self.activity.save(update_fields=["activity_type"])

        (
            quiz,
            question_one,
            question_two,
        ) = self.create_quiz()

        self.client.force_login(self.student)

        correct_one = (
            question_one.choices
            .get(is_correct=True)
        )

        wrong_two = (
            question_two.choices
            .get(is_correct=False)
        )

        response = self.client.post(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                f"question_{question_one.id}": str(correct_one.id),
                f"question_{question_two.id}": str(wrong_two.id),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        attempt = (
            QuizAttempt.objects
            .filter(
                quiz=quiz,
                student=self.student,
            )
            .latest("created_at")
        )

        review_response = self.client.get(
            reverse(
                "quiz_attempt_review",
                args=[
                    self.course.slug,
                    attempt.id,
                ],
            )
        )

        self.assertEqual(
            review_response.status_code,
            200,
        )

        self.assertContains(
            review_response,
            question_one.question_text,
        )

        self.assertContains(
            review_response,
            question_two.question_text,
        )

        self.assertContains(
            review_response,
            "A programming language",
        )
        self.assertContains(
            review_response,
            "Correct",
        )

        self.assertContains(
            review_response,
            "Incorrect",
        )

        self.assertContains(
            review_response,
            "50.0%",
        )

    def test_quiz_retry_preserves_previous_pass(self):
        self.enroll_student()

        self.activity.activity_type = "quiz"
        self.activity.save(update_fields=["activity_type"])

        (
            quiz,
            question_one,
            question_two,
        ) = self.create_quiz()

        self.client.force_login(self.student)

        correct_one = (
            question_one.choices
            .get(is_correct=True)
        )

        correct_two = (
            question_two.choices
            .get(is_correct=True)
        )

        wrong_one = (
            question_one.choices
            .get(is_correct=False)
        )

        wrong_two = (
            question_two.choices
            .get(is_correct=False)
        )

        # First attempt: pass.
        first_response = self.client.post(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                f"question_{question_one.id}": str(correct_one.id),
                f"question_{question_two.id}": str(correct_two.id),
            },
        )

        self.assertEqual(
            first_response.status_code,
            200,
        )

        first_attempt = (
            QuizAttempt.objects
            .filter(
                quiz=quiz,
                student=self.student,
            )
            .latest("created_at")
        )

        self.assertTrue(
            first_attempt.passed
        )

        self.assertEqual(
            first_attempt.score,
            20,
        )

        self.assertTrue(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=self.activity,
            ).exists()
        )

        # Second attempt: fail.
        second_response = self.client.post(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                f"question_{question_one.id}": str(wrong_one.id),
                f"question_{question_two.id}": str(wrong_two.id),
            },
        )

        self.assertEqual(
            second_response.status_code,
            200,
        )

        second_attempt = (
            QuizAttempt.objects
            .filter(
                quiz=quiz,
                student=self.student,
            )
            .latest("created_at")
        )

        self.assertFalse(
            second_attempt.passed
        )

        self.assertEqual(
            second_attempt.score,
            0,
        )

        # The previous successful completion must remain.
        self.assertTrue(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=self.activity,
            ).exists()
        )

        self.assertEqual(
            QuizAttempt.objects.filter(
                quiz=quiz,
                student=self.student,
            ).count(),
            2,
        )

        # The retry UI should be visible after the second attempt.
        self.assertContains(
            second_response,
            "Retake Quiz",
        )

        self.assertContains(
            second_response,
            "Review Attempt",
        )

    def test_course_average_uses_best_quiz_attempt(self):
        self.enroll_student()

        self.activity.activity_type = "quiz"
        self.activity.save(update_fields=["activity_type"])

        (
            quiz,
            question_one,
            question_two,
        ) = self.create_quiz()

        self.client.force_login(self.student)

        correct_one = (
            question_one.choices
            .get(is_correct=True)
        )

        correct_two = (
            question_two.choices
            .get(is_correct=True)
        )

        wrong_one = (
            question_one.choices
            .get(is_correct=False)
        )

        wrong_two = (
            question_two.choices
            .get(is_correct=False)
        )

        # First attempt: 100%.
        response = self.client.post(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                f"question_{question_one.id}": str(correct_one.id),
                f"question_{question_two.id}": str(correct_two.id),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        # Second attempt: 0%.
        response = self.client.post(
            reverse(
                "quiz_take",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            {
                f"question_{question_one.id}": str(wrong_one.id),
                f"question_{question_two.id}": str(wrong_two.id),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        progress_response = self.client.get(
            reverse(
                "course_progress",
                args=[self.course.slug],
            )
        )

        self.assertEqual(
            progress_response.status_code,
            200,
        )

        progress = progress_response.context["progress"]

        self.assertEqual(
            progress["average_score"],
            100.0,
        )

        self.assertEqual(
            QuizAttempt.objects.filter(
                quiz=quiz,
                student=self.student,
            ).count(),
            2,
        )

        self.assertTrue(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=self.activity,
            ).exists()
        )

    def test_quiz_models_are_available_in_admin(self):
        quiz, question_one, question_two = self.create_quiz()

        admin_user = User.objects.create_superuser(
            username="quiz_admin",
            email="quiz_admin@example.com",
            password="test-admin-password",
        )

        self.client.force_login(admin_user)

        quiz_list_response = self.client.get(
            reverse(
                "admin:academy_quiz_changelist"
            )
        )

        self.assertEqual(
            quiz_list_response.status_code,
            200,
        )

        self.assertContains(
            quiz_list_response,
            self.activity.title,
        )

        question_list_response = self.client.get(
            reverse(
                "admin:academy_quizquestion_changelist"
            )
        )

        self.assertEqual(
            question_list_response.status_code,
            200,
        )

        self.assertContains(
            question_list_response,
            question_one.question_text,
        )

        choice_list_response = self.client.get(
            reverse(
                "admin:academy_quizchoice_changelist"
            )
        )

        self.assertEqual(
            choice_list_response.status_code,
            200,
        )

    def test_student_cannot_access_instructor_quizzes(self):
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("instructor_quizzes")
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_instructor_can_manage_quizzes(self):
        self.activity.activity_type = "quiz"
        self.activity.save(
            update_fields=["activity_type"]
        )

        quiz, question_one, question_two = (
            self.create_quiz()
        )

        self.client.force_login(
            self.instructor
        )

        response = self.client.get(
            reverse("instructor_quizzes")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            self.activity.title,
        )

        response = self.client.get(
            reverse(
                "instructor_quiz_edit",
                args=[quiz.id],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            question_one.question_text,
        )

    def test_instructor_can_add_question_and_choice(self):
        self.activity.activity_type = "quiz"
        self.activity.save(
            update_fields=["activity_type"]
        )

        quiz, question_one, question_two = (
            self.create_quiz()
        )

        self.client.force_login(
            self.instructor
        )

        response = self.client.post(
            reverse(
                "instructor_quiz_edit",
                args=[quiz.id],
            ),
            {
                "action": "add_question",
                "question_text": "What is an if statement?",
                "points": "5",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        new_question = (
            QuizQuestion.objects
            .get(
                quiz=quiz,
                question_text="What is an if statement?",
            )
        )

        response = self.client.post(
            reverse(
                "instructor_quiz_edit",
                args=[quiz.id],
            ),
            {
                "action": "add_choice",
                "question_id": str(new_question.id),
                "choice_text": "A decision-making statement",
                "is_correct": "on",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        choice = (
            QuizChoice.objects
            .get(
                question=new_question,
                choice_text="A decision-making statement",
            )
        )

        self.assertTrue(
            choice.is_correct
        )

        quiz.activity.refresh_from_db()

        self.assertEqual(
            quiz.activity.max_score,
            25,
        )

    def test_instructor_choice_correct_answer_is_exclusive(self):
        self.activity.activity_type = "quiz"
        self.activity.save(
            update_fields=["activity_type"]
        )

        quiz, question_one, question_two = (
            self.create_quiz()
        )

        choice_one = QuizChoice.objects.create(
            question=question_one,
            choice_text="First answer",
            is_correct=True,
            order=3,
        )

        choice_two = QuizChoice.objects.create(
            question=question_one,
            choice_text="Second answer",
            is_correct=False,
            order=4,
        )

        self.client.force_login(
            self.instructor
        )

        response = self.client.post(
            reverse(
                "instructor_quiz_edit",
                args=[quiz.id],
            ),
            {
                "action": "update_choice",
                "choice_id": str(choice_two.id),
                "choice_text": "Second answer",
                "order": "4",
                "is_correct": "on",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        choice_one.refresh_from_db()
        choice_two.refresh_from_db()

        self.assertFalse(
            choice_one.is_correct
        )

        self.assertTrue(
            choice_two.is_correct
        )

    def test_instructor_quiz_validation_detects_missing_correct_answer(self):
        self.activity.activity_type = "quiz"
        self.activity.save(
            update_fields=["activity_type"]
        )

        quiz, question_one, question_two = (
            self.create_quiz()
        )

        # Remove the correct flag from every choice.
        QuizChoice.objects.filter(
            question=question_one
        ).update(
            is_correct=False
        )

        self.client.force_login(
            self.instructor
        )

        response = self.client.get(
            reverse(
                "instructor_quiz_edit",
                args=[quiz.id],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.context["quiz_ready"]
        )

        self.assertContains(
            response,
            "Question 1 must have exactly one correct answer.",
        )

    def test_instructor_can_delete_choice(self):
        self.activity.activity_type = "quiz"
        self.activity.save(
            update_fields=["activity_type"]
        )

        quiz, question_one, question_two = (
            self.create_quiz()
        )

        choice = (
            question_one.choices
            .filter(is_correct=False)
            .first()
        )

        self.assertIsNotNone(
            choice
        )

        self.client.force_login(
            self.instructor
        )

        response = self.client.post(
            reverse(
                "instructor_quiz_edit",
                args=[quiz.id],
            ),
            {
                "action": "delete_choice",
                "choice_id": str(choice.id),
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertFalse(
            QuizChoice.objects.filter(
                id=choice.id
            ).exists()
        )


# ============================================================
# INSTRUCTOR COURSE CONTENT MANAGEMENT TESTS
# ============================================================

class InstructorContentManagementTests(TestCase):

    def setUp(self):
        self.student = User.objects.create_user(
            username="content_student",
            password="testpass123",
        )

        self.instructor = User.objects.create_user(
            username="content_instructor",
            password="testpass123",
        )

        self.instructor.role = "INSTRUCTOR"
        self.instructor.save()

        self.course = Course.objects.create(
            title="Content Management Course",
            slug="content-management-course",
            description="Test course",
            instructor="Coding E-Learning Platform",
            duration="4 weeks",
            level="Beginner",
        )

    def test_student_cannot_access_instructor_content(self):
        self.client.login(
            username="content_student",
            password="testpass123",
        )

        response = self.client.get(
            reverse("instructor_content_management")
        )

        self.assertEqual(response.status_code, 403)

    def test_instructor_can_view_course_content_management(self):
        self.client.login(
            username="content_instructor",
            password="testpass123",
        )

        response = self.client.get(
            reverse("instructor_content_management")
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Content Management Course",
        )

    def test_instructor_can_add_module_lesson_and_quiz_activity(self):
        self.client.login(
            username="content_instructor",
            password="testpass123",
        )

        response = self.client.post(
            reverse(
                "instructor_course_content",
                kwargs={
                    "course_id": self.course.id,
                },
            ),
            {
                "action": "add_module",
                "title": "Python Fundamentals",
                "description": "Core Python concepts",
                "order": "1",
            },
        )

        self.assertEqual(response.status_code, 302)

        module = Module.objects.get(
            course=self.course,
            title="Python Fundamentals",
        )

        response = self.client.post(
            reverse(
                "instructor_course_content",
                kwargs={
                    "course_id": self.course.id,
                },
            ),
            {
                "action": "add_lesson",
                "module_id": module.id,
                "title": "Conditional Statements",
                "content": "Learn if, elif and else.",
                "order": "1",
            },
        )

        self.assertEqual(response.status_code, 302)

        lesson = Lesson.objects.get(
            module=module,
            title="Conditional Statements",
        )

        response = self.client.post(
            reverse(
                "instructor_course_content",
                kwargs={
                    "course_id": self.course.id,
                },
            ),
            {
                "action": "add_activity",
                "lesson_id": lesson.id,
                "title": "Conditional Statements Quiz",
                "activity_type": "quiz",
                "instructions": "Complete the quiz.",
                "order": "1",
                "max_score": "50",
                "is_required": "on",
            },
        )

        self.assertEqual(response.status_code, 302)

        activity = Activity.objects.get(
            lesson=lesson,
            title="Conditional Statements Quiz",
        )

        self.assertEqual(
            activity.activity_type,
            "quiz",
        )

        self.assertEqual(
            activity.max_score,
            50,
        )

        self.assertTrue(
            activity.is_required,
        )

        from .models import Quiz

        self.assertTrue(
            Quiz.objects.filter(
                activity=activity
            ).exists()
        )

    def test_instructor_can_edit_lesson_and_activity(self):
        self.client.login(
            username="content_instructor",
            password="testpass123",
        )

        module = Module.objects.create(
            course=self.course,
            title="Original Module",
            description="Original description",
            order=1,
        )

        lesson = Lesson.objects.create(
            course=self.course,
            module=module,
            title="Original Lesson",
            content="Original content",
            order=1,
        )

        activity = Activity.objects.create(
            lesson=lesson,
            title="Original Activity",
            activity_type="coding",
            instructions="Original instructions",
            order=1,
            max_score=20,
            is_required=True,
        )

        response = self.client.post(
            reverse(
                "instructor_course_content",
                kwargs={
                    "course_id": self.course.id,
                },
            ),
            {
                "action": "edit_lesson",
                "lesson_id": lesson.id,
                "module_id": module.id,
                "title": "Updated Lesson",
                "content": "Updated content",
                "order": "2",
            },
        )

        self.assertEqual(response.status_code, 302)

        lesson.refresh_from_db()

        self.assertEqual(
            lesson.title,
            "Updated Lesson",
        )

        self.assertEqual(
            lesson.content,
            "Updated content",
        )

        self.assertEqual(
            lesson.order,
            2,
        )

        response = self.client.post(
            reverse(
                "instructor_course_content",
                kwargs={
                    "course_id": self.course.id,
                },
            ),
            {
                "action": "edit_activity",
                "activity_id": activity.id,
                "lesson_id": lesson.id,
                "title": "Updated Activity",
                "activity_type": "coding",
                "instructions": "Updated instructions",
                "order": "2",
                "max_score": "30",
                "is_required": "on",
            },
        )

        self.assertEqual(response.status_code, 302)

        activity.refresh_from_db()

        self.assertEqual(
            activity.title,
            "Updated Activity",
        )

        self.assertEqual(
            activity.instructions,
            "Updated instructions",
        )

        self.assertEqual(
            activity.order,
            2,
        )

        self.assertEqual(
            activity.max_score,
            30,
        )

        self.assertTrue(
            activity.is_required,
        )


# ============================================================
# INSTRUCTOR DASHBOARD TESTS
# ============================================================

class InstructorDashboardTests(TestCase):

    def setUp(self):

        self.student = User.objects.create_user(
            username="dashboard_student",
            password="testpass123",
        )

        self.instructor = User.objects.create_user(
            username="dashboard_instructor",
            password="testpass123",
        )

        self.instructor.role = "INSTRUCTOR"
        self.instructor.save()

        self.course = Course.objects.create(
            title="Dashboard Course",
            slug="dashboard-course",
            description="Dashboard test course",
            instructor="Coding E-Learning Platform",
            duration="4 weeks",
            level="Beginner",
        )


    def test_student_cannot_access_instructor_dashboard(self):

        self.client.login(
            username="dashboard_student",
            password="testpass123",
        )

        response = self.client.get(
            reverse("instructor_dashboard")
        )

        self.assertEqual(
            response.status_code,
            403,
        )


    def test_instructor_can_view_dashboard(self):

        self.client.login(
            username="dashboard_instructor",
            password="testpass123",
        )

        response = self.client.get(
            reverse("instructor_dashboard")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Instructor Dashboard",
        )

        self.assertContains(
            response,
            "Dashboard Course",
        )


    def test_dashboard_displays_content_counts(self):

        self.client.login(
            username="dashboard_instructor",
            password="testpass123",
        )

        module = Module.objects.create(
            course=self.course,
            title="Dashboard Module",
            description="Test module",
            order=1,
        )

        lesson = Lesson.objects.create(
            course=self.course,
            module=module,
            title="Dashboard Lesson",
            content="Test lesson",
            order=1,
        )

        Activity.objects.create(
            lesson=lesson,
            title="Dashboard Activity",
            activity_type="reading",
            instructions="Test activity",
            order=1,
            max_score=10,
            is_required=True,
        )

        response = self.client.get(
            reverse("instructor_dashboard")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Dashboard Course",
        )

        self.assertContains(
            response,
            "Modules",
        )


    def test_instructor_navigation_links_are_available(self):

        self.client.login(
            username="dashboard_instructor",
            password="testpass123",
        )

        dashboard = self.client.get(
            reverse("instructor_dashboard")
        )

        self.assertEqual(
            dashboard.status_code,
            200,
        )

        self.assertContains(
            dashboard,
            reverse("instructor_dashboard"),
        )

        self.assertContains(
            dashboard,
            reverse("instructor_content_management"),
        )

        self.assertContains(
            dashboard,
            reverse("instructor_quizzes"),
        )

        self.assertContains(
            dashboard,
            reverse("instructor_submissions"),
        )

        content = self.client.get(
            reverse("instructor_content_management")
        )

        self.assertEqual(
            content.status_code,
            200,
        )

        self.assertContains(
            content,
            reverse("instructor_dashboard"),
        )

        self.assertContains(
            content,
            reverse("instructor_quizzes"),
        )

        self.assertContains(
            content,
            reverse("instructor_submissions"),
        )





# ============================================================
# ASSIGNMENT / LAB SUBMISSION TESTS
# ============================================================

class AssignmentLabSubmissionTests(TestCase):

    def setUp(self):

        self.student = User.objects.create_user(
            username="assignment_lab_student",
            password="testpass123",
        )

        self.instructor = User.objects.create_user(
            username="assignment_lab_instructor",
            password="testpass123",
            role="INSTRUCTOR",
        )

        self.other_student = User.objects.create_user(
            username="assignment_lab_other_student",
            password="testpass123",
        )

        self.course = Course.objects.create(
            title="Assignment Lab Test Course",
            slug="assignment-lab-test-course",
            description="Test course",
            instructor="Coding E-Learning Platform",
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Test Module",
            order=1,
        )

        self.lesson = Lesson.objects.create(
            course=self.course,
            module=self.module,
            title="Test Lesson",
            order=1,
        )

        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )


    def test_assignment_submission_creates_pending_submission(self):

        assignment = Activity.objects.create(
            lesson=self.lesson,
            title="Assignment Submission Test",
            activity_type="assignment",
            instructions="Complete the assignment.",
            order=1,
            max_score=20,
            is_required=True,
        )

        self.client.force_login(self.student)

        url = reverse(
            "activity_detail",
            kwargs={
                "course_slug": self.course.slug,
                "lesson_id": self.lesson.id,
                "activity_id": assignment.id,
            },
        )

        response = self.client.post(
            url,
            {
                "submit_activity": "1",
                "response_text": "This is my completed assignment.",
                "github_url": "https://github.com/example/assignment",
            },
        )

        self.assertEqual(response.status_code, 200)

        submission = Submission.objects.get(
            student=self.student,
            activity=assignment,
        )

        self.assertEqual(
            submission.response_text,
            "This is my completed assignment.",
        )

        self.assertEqual(
            submission.github_url,
            "https://github.com/example/assignment",
        )

        self.assertEqual(submission.code, "")
        self.assertEqual(submission.status, "submitted")

        self.assertFalse(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=assignment,
            ).exists()
        )


    def test_lab_submission_creates_pending_submission(self):

        lab = Activity.objects.create(
            lesson=self.lesson,
            title="Lab Submission Test",
            activity_type="lab",
            instructions="Complete the lab.",
            order=1,
            max_score=30,
            is_required=True,
        )

        self.client.force_login(self.student)

        url = reverse(
            "activity_detail",
            kwargs={
                "course_slug": self.course.slug,
                "lesson_id": self.lesson.id,
                "activity_id": lab.id,
            },
        )

        response = self.client.post(
            url,
            {
                "submit_activity": "1",
                "response_text": "Lab completed and tested successfully.",
            },
        )

        self.assertEqual(response.status_code, 200)

        submission = Submission.objects.get(
            student=self.student,
            activity=lab,
        )

        self.assertEqual(
            submission.response_text,
            "Lab completed and tested successfully.",
        )

        self.assertEqual(submission.status, "submitted")

        self.assertFalse(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=lab,
            ).exists()
        )


    def test_assignment_requires_submission_content(self):

        assignment = Activity.objects.create(
            lesson=self.lesson,
            title="Assignment Validation Test",
            activity_type="assignment",
            instructions="Submit your work.",
            order=1,
            max_score=20,
            is_required=True,
        )

        self.client.force_login(self.student)

        url = reverse(
            "activity_detail",
            kwargs={
                "course_slug": self.course.slug,
                "lesson_id": self.lesson.id,
                "activity_id": assignment.id,
            },
        )

        response = self.client.post(
            url,
            {
                "submit_activity": "1",
                "response_text": "",
                "github_url": "",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Please provide at least one submission item",
        )

        self.assertFalse(
            Submission.objects.filter(
                student=self.student,
                activity=assignment,
            ).exists()
        )

    def test_assignment_submission_accepts_attachment(self):

        assignment = Activity.objects.create(
            lesson=self.lesson,
            title="Assignment Attachment Test",
            activity_type="assignment",
            instructions="Upload your solution.",
            order=2,
            max_score=20,
            is_required=True,
        )

        self.client.force_login(self.student)

        uploaded_file = SimpleUploadedFile(
            "solution.txt",
            b"Python assignment solution",
            content_type="text/plain",
        )

        response = self.client.post(
            reverse(
                "activity_detail",
                kwargs={
                    "course_slug": self.course.slug,
                    "lesson_id": self.lesson.id,
                    "activity_id": assignment.id,
                },
            ),
            {
                "submit_activity": "1",
                "response_text": "",
                "github_url": "",
                "attachment": uploaded_file,
            },
        )

        self.assertEqual(response.status_code, 200)

        submission = Submission.objects.get(
            student=self.student,
            activity=assignment,
        )

        self.assertTrue(bool(submission.attachment))
        attachment_name = submission.attachment.name.rsplit("/", 1)[-1]

        self.assertTrue(
            attachment_name.startswith("solution")
        )
        self.assertTrue(
            attachment_name.endswith(".txt")
        )

        submission.attachment.close()
        submission.attachment.delete(save=False)


    def test_assignment_rejects_unsupported_attachment(self):

        assignment = Activity.objects.create(
            lesson=self.lesson,
            title="Assignment File Validation Test",
            activity_type="assignment",
            instructions="Upload your solution.",
            order=3,
            max_score=20,
            is_required=True,
        )

        self.client.force_login(self.student)

        uploaded_file = SimpleUploadedFile(
            "malicious.html",
            b"<script>alert('test')</script>",
            content_type="text/html",
        )

        response = self.client.post(
            reverse(
                "activity_detail",
                kwargs={
                    "course_slug": self.course.slug,
                    "lesson_id": self.lesson.id,
                    "activity_id": assignment.id,
                },
            ),
            {
                "submit_activity": "1",
                "attachment": uploaded_file,
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Unsupported attachment type",
        )

        self.assertFalse(
            Submission.objects.filter(
                student=self.student,
                activity=assignment,
            ).exists()
        )


    def test_instructor_grading_completes_assignment(self):

        assignment = Activity.objects.create(
            lesson=self.lesson,
            title="Assignment Grading Test",
            activity_type="assignment",
            instructions="Complete and submit.",
            order=4,
            max_score=20,
            is_required=True,
        )

        submission = Submission.objects.create(
            student=self.student,
            activity=assignment,
            code="",
            response_text="Completed assignment work.",
            github_url="https://github.com/example/assignment",
        )

        self.client.force_login(self.instructor)

        response = self.client.post(
            reverse(
                "review_submission",
                args=[submission.id],
            ),
            {
                "score": "17",
                "feedback": "Good work. Add more input validation.",
            },
        )

        self.assertEqual(response.status_code, 302)

        submission.refresh_from_db()

        self.assertEqual(submission.score, 17)
        self.assertEqual(submission.status, "graded")
        self.assertEqual(
            submission.feedback,
            "Good work. Add more input validation.",
        )

        self.assertTrue(
            ActivityCompletion.objects.filter(
                student=self.student,
                activity=assignment,
            ).exists()
        )


    def test_instructor_review_displays_assignment_materials(self):

        assignment = Activity.objects.create(
            lesson=self.lesson,
            title="Assignment Review Display Test",
            activity_type="assignment",
            instructions="Review student work.",
            order=6,
            max_score=20,
            is_required=True,
        )

        submission = Submission.objects.create(
            student=self.student,
            activity=assignment,
            code="",
            response_text="Student explanation",
            github_url="https://github.com/example/review",
        )

        self.client.force_login(self.instructor)

        response = self.client.get(
            reverse(
                "review_submission",
                args=[submission.id],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Student Response",
        )

        self.assertContains(
            response,
            "Student explanation",
        )

        self.assertContains(
            response,
            "GitHub Submission",
        )

        self.assertContains(
            response,
            "https://github.com/example/review",
        )


    def test_submission_attachment_is_owner_or_instructor_only(self):

        assignment = Activity.objects.create(
            lesson=self.lesson,
            title="Attachment Permission Test",
            activity_type="assignment",
            instructions="Review attachment access.",
            order=5,
            max_score=10,
            is_required=True,
        )

        uploaded_file = SimpleUploadedFile(
            "private.txt",
            b"Private submission",
            content_type="text/plain",
        )

        submission = Submission.objects.create(
            student=self.student,
            activity=assignment,
            code="",
            attachment=uploaded_file,
        )

        url = reverse(
            "submission_attachment",
            args=[submission.id],
        )

        self.client.force_login(self.other_student)

        forbidden = self.client.get(url)

        self.assertEqual(
            forbidden.status_code,
            403,
        )

        self.client.force_login(self.student)

        owner_response = self.client.get(url)

        self.assertEqual(
            owner_response.status_code,
            200,
        )

        self.client.force_login(self.instructor)

        instructor_response = self.client.get(url)

        self.assertEqual(
            instructor_response.status_code,
            200,
        )

        submission.attachment.delete(save=False)


# ============================================================
# UI / NAVIGATION INTEGRATION TESTS
# ============================================================

class UiNavigationIntegrationTests(TestCase):

    def setUp(self):

        self.student = User.objects.create_user(
            username="ui_student",
            password="testpass123",
        )

        self.instructor = User.objects.create_user(
            username="ui_instructor",
            password="testpass123",
        )

        self.instructor.role = "INSTRUCTOR"
        self.instructor.save()


    def test_student_navigation_renders_consistently(self):

        self.client.login(
            username="ui_student",
            password="testpass123",
        )

        response = self.client.get(
            reverse("course_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Coding Academy",
        )

        self.assertContains(
            response,
            reverse("home"),
        )

        self.assertContains(
            response,
            reverse("course_list"),
        )

        self.assertContains(
            response,
            reverse("my_courses"),
        )

        self.assertContains(
            response,
            reverse("logout"),
        )


    def test_instructor_navigation_exposes_instructor_dashboard(self):

        self.client.login(
            username="ui_instructor",
            password="testpass123",
        )

        response = self.client.get(
            reverse("course_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            reverse("instructor_dashboard"),
        )

        self.assertContains(
            response,
            "Instructor",
        )


class StudentAssessmentHistoryTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="assessment_student",
            password="StrongPass123!",
            role="STUDENT",
        )

        self.other_student = User.objects.create_user(
            username="other_student",
            password="StrongPass123!",
            role="STUDENT",
        )

        self.course = Course.objects.create(
            title="Assessment Test Course",
            description="Assessment test course",
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
            title="Python Basics",
            content="Learn Python basics.",
            order=1,
        )

        self.activity = Activity.objects.create(
            lesson=self.lesson,
            title="Python Exercise",
            activity_type="coding",
            instructions="Write Python code.",
            order=1,
            max_score=20,
            is_required=True,
        )

    def test_assessment_history_requires_login(self):
        response = self.client.get(
            reverse("student_assessment_history")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_student_sees_only_own_submissions(self):
        own_submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Mine")',
            score=18,
            status="graded",
            feedback="Good work.",
        )

        Submission.objects.create(
            student=self.other_student,
            activity=self.activity,
            code='print("Other student")',
            score=10,
            status="graded",
            feedback="Other feedback.",
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse("student_assessment_history")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "print(&quot;Mine&quot;)",
        )

        self.assertContains(
            response,
            "18",
        )

        self.assertContains(
            response,
            "Good work.",
        )

        self.assertNotContains(
            response,
            "Other student",
        )

        self.assertNotContains(
            response,
            "Other feedback.",
        )

        self.assertTrue(
            Submission.objects.filter(
                id=own_submission.id,
                student=self.student,
            ).exists()
        )

    def test_assessment_history_status_filters(self):
        Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Pending")',
            status="submitted",
        )

        Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Graded")',
            score=20,
            status="graded",
            feedback="Excellent.",
        )

        Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Error")',
            status="error",
        )

        self.client.force_login(self.student)

        pending_response = self.client.get(
            reverse("student_assessment_history"),
            {"status": "pending"},
        )

        self.assertEqual(
            pending_response.status_code,
            200,
        )

        self.assertContains(
            pending_response,
            "print(&quot;Pending&quot;)",
        )

        self.assertNotContains(
            pending_response,
            "print(&quot;Graded&quot;)",
        )

        graded_response = self.client.get(
            reverse("student_assessment_history"),
            {"status": "graded"},
        )

        self.assertEqual(
            graded_response.status_code,
            200,
        )

        self.assertContains(
            graded_response,
            "Excellent.",
        )

        error_response = self.client.get(
            reverse("student_assessment_history"),
            {"status": "error"},
        )

        self.assertEqual(
            error_response.status_code,
            200,
        )

        self.assertContains(
            error_response,
            "Needs Correction",
        )


class StudentResubmissionTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="resubmit_student",
            password="StrongPass123!",
            role="STUDENT",
        )

        self.other_student = User.objects.create_user(
            username="resubmit_other",
            password="StrongPass123!",
            role="STUDENT",
        )

        self.course = Course.objects.create(
            title="Resubmission Test Course",
            description="Resubmission test course",
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
            title="Corrections",
            content="Correct your work.",
            order=1,
        )

        self.activity = Activity.objects.create(
            lesson=self.lesson,
            title="Correction Exercise",
            activity_type="coding",
            instructions="Correct the submitted program.",
            order=1,
            max_score=20,
            is_required=True,
        )

    def test_resubmission_requires_login(self):
        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Fix me")',
            status="error",
        )

        response = self.client.get(
            reverse(
                "student_resubmit_submission",
                args=[submission.id],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_student_can_open_own_correction_for_resubmission(self):
        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Fix me")',
            status="error",
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "student_resubmit_submission",
                args=[submission.id],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            reverse(
                "activity_detail",
                args=[
                    self.course.slug,
                    self.lesson.id,
                    self.activity.id,
                ],
            ),
            response.url,
        )

    def test_student_cannot_resubmit_another_students_submission(self):
        submission = Submission.objects.create(
            student=self.other_student,
            activity=self.activity,
            code='print("Other work")',
            status="error",
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "student_resubmit_submission",
                args=[submission.id],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    @override_settings(DEBUG=True)
    def test_student_resubmission_creates_new_submission_and_preserves_history(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        original = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Needs correction")',
            status="correction",
            score=5,
            feedback="Please correct the program.",
        )

        self.client.force_login(self.student)

        redirect_response = self.client.get(
            reverse(
                "student_resubmit_submission",
                args=[original.id],
            )
        )

        self.assertEqual(
            redirect_response.status_code,
            302,
        )

        activity_url = reverse(
            "activity_detail",
            args=[
                self.course.slug,
                self.lesson.id,
                self.activity.id,
            ],
        )

        self.assertIn(
            activity_url,
            redirect_response.url,
        )

        submit_response = self.client.post(
            activity_url,
            {
                "code": 'print("Corrected work")',
                "program_input": "",
                "submit_activity": "1",
            },
        )

        self.assertEqual(
            submit_response.status_code,
            200,
        )

        submissions = Submission.objects.filter(
            student=self.student,
            activity=self.activity,
        ).order_by(
            "-submitted_at",
            "-id",
        )

        self.assertEqual(
            submissions.count(),
            2,
        )

        latest = submissions.first()

        self.assertEqual(
            latest.status,
            "submitted",
        )

        self.assertEqual(
            latest.code,
            'print("Corrected work")',
        )

        self.assertEqual(
            submissions.last().id,
            original.id,
        )

        original.refresh_from_db()

        self.assertEqual(
            original.status,
            "correction",
        )

        self.assertEqual(
            original.feedback,
            "Please correct the program.",
        )


    def test_non_error_submission_does_not_enter_resubmission_flow(self):
        submission = Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Already graded")',
            score=18,
            status="graded",
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "student_resubmit_submission",
                args=[submission.id],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            reverse(
                "student_assessment_history"
            ),
            response.url,
        )

    def test_assessment_history_shows_resubmit_for_correction(self):
        Submission.objects.create(
            student=self.student,
            activity=self.activity,
            code='print("Needs correction")',
            status="error",
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse("student_assessment_history")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Correct &amp; Resubmit",
        )
