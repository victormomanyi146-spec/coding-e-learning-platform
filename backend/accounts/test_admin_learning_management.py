from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from academy.models import Activity, Course, Lesson, Module, Quiz
from accounts.models import User

class AdminLearningManagementTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="learning_admin", email="learning_admin@example.com", password="StrongAdminPass!2026")
        token, _ = Token.objects.get_or_create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.courses_url = reverse("admin-learning-resource", kwargs={"resource":"courses"})

    def test_admin_can_list_and_create_courses(self):
        self.assertEqual(self.client.get(self.courses_url).status_code, 200)
        response = self.client.post(self.courses_url, {"title":"Admin API Course", "slug":"admin-api-course", "description":"Course managed in the admin workspace.", "instructor":"Tech Haven", "duration":"4 weeks", "level":"Beginner"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Course.objects.filter(slug="admin-api-course").exists())

    def test_admin_can_update_existing_content(self):
        course = Course.objects.create(title="Content Course", slug="content-course", description="Before", instructor="Tech Haven", duration="3 weeks", level="Beginner")
        url = reverse("admin-learning-resource-detail", kwargs={"resource":"courses", "item_id":course.id})
        response = self.client.patch(url, {"description":"Updated from admin workspace."}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        course.refresh_from_db(); self.assertEqual(course.description, "Updated from admin workspace.")

    def test_lesson_rejects_module_from_another_course(self):
        one = Course.objects.create(title="Course One", slug="course-one", description="One", instructor="Test", duration="1 week", level="Beginner")
        two = Course.objects.create(title="Course Two", slug="course-two", description="Two", instructor="Test", duration="1 week", level="Beginner")
        module = Module.objects.create(course=one, title="Module One", order=1)
        url = reverse("admin-learning-resource", kwargs={"resource":"lessons"})
        response = self.client.post(url, {"course":two.id,"module":module.id,"title":"Bad relationship","content":"Lesson body","order":1}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Lesson.objects.filter(title="Bad relationship").exists())

    def test_enrollments_are_read_only(self):
        response = self.client.post(reverse("admin-learning-resource", kwargs={"resource":"enrollments"}), {}, format="json")
        self.assertEqual(response.status_code, 405)

    def test_non_admin_cannot_access_learning_management(self):
        student = User.objects.create_user(username="learning_student", email="student@example.com", password="StrongStudentPass!2026", role=User.Roles.STUDENT)
        self.client.force_authenticate(user=student)
        self.assertEqual(self.client.get(self.courses_url).status_code, 403)

    def test_quiz_must_use_quiz_activity(self):
        course = Course.objects.create(title="Quiz Course", slug="quiz-course", description="Test", instructor="Test", duration="1 week", level="Beginner")
        lesson = Lesson.objects.create(course=course, title="Lesson", content="Body", order=1)
        activity = Activity.objects.create(lesson=lesson, title="Not a quiz", activity_type="reading", instructions="Read", order=1, max_score=10)
        response = self.client.post(reverse("admin-learning-resource", kwargs={"resource":"quizzes"}), {"activity":activity.id,"passing_score":50}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Quiz.objects.filter(activity=activity).exists())
