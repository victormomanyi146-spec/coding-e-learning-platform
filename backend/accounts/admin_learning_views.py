from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from academy.models import Activity, Certificate, Course, Enrollment, Lesson, Module, Quiz, QuizChoice, QuizQuestion, Submission
from .views import IsPlatformSuperuser

class AdminCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "title", "slug", "description", "instructor", "duration", "level", "created_at"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

class AdminModuleSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    class Meta:
        model = Module
        fields = ["id", "course", "course_title", "title", "description", "order", "created_at"]
        read_only_fields = ["id", "created_at", "course_title"]

class AdminLessonSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    module_title = serializers.CharField(source="module.title", read_only=True, allow_null=True)
    class Meta:
        model = Lesson
        fields = ["id", "course", "course_title", "module", "module_title", "title", "content", "order", "created_at"]
        read_only_fields = ["id", "created_at", "course_title", "module_title"]
    def validate(self, attrs):
        course = attrs.get("course", getattr(self.instance, "course", None))
        module = attrs.get("module", getattr(self.instance, "module", None))
        if module is not None and course is not None and module.course_id != course.id:
            raise serializers.ValidationError({"module": "The selected module must belong to the selected course."})
        return attrs

class AdminActivitySerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    course_title = serializers.CharField(source="lesson.course.title", read_only=True)
    class Meta:
        model = Activity
        fields = ["id", "lesson", "lesson_title", "course_title", "title", "activity_type", "instructions", "order", "max_score", "is_required", "created_at"]
        read_only_fields = ["id", "created_at", "lesson_title", "course_title"]

class AdminQuizSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="activity.title", read_only=True)
    lesson_title = serializers.CharField(source="activity.lesson.title", read_only=True)
    course_title = serializers.CharField(source="activity.lesson.course.title", read_only=True)
    class Meta:
        model = Quiz
        fields = ["id", "activity", "quiz_title", "lesson_title", "course_title", "passing_score", "created_at"]
        read_only_fields = ["id", "created_at", "quiz_title", "lesson_title", "course_title"]
    def validate_activity(self, value):
        if value.activity_type != "quiz":
            raise serializers.ValidationError("A quiz must be connected to an activity of type 'quiz'.")
        return value

class AdminQuizQuestionSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.activity.title", read_only=True)
    course_title = serializers.CharField(source="quiz.activity.lesson.course.title", read_only=True)
    class Meta:
        model = QuizQuestion
        fields = ["id", "quiz", "quiz_title", "course_title", "question_text", "order", "points", "is_active"]
        read_only_fields = ["id", "quiz_title", "course_title"]

class AdminQuizChoiceSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.question_text", read_only=True)
    quiz_title = serializers.CharField(source="question.quiz.activity.title", read_only=True)
    class Meta:
        model = QuizChoice
        fields = ["id", "question", "question_text", "quiz_title", "choice_text", "is_correct", "order"]
        read_only_fields = ["id", "question_text", "quiz_title"]

class AdminEnrollmentSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source="student.username", read_only=True)
    student_email = serializers.EmailField(source="student.email", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    class Meta:
        model = Enrollment
        fields = ["id", "student", "student_username", "student_email", "course", "course_title", "enrolled_at"]
        read_only_fields = fields

class AdminSubmissionSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source="student.username", read_only=True)
    activity_title = serializers.CharField(source="activity.title", read_only=True)
    course_title = serializers.CharField(source="activity.lesson.course.title", read_only=True)
    class Meta:
        model = Submission
        fields = ["id", "student_username", "activity_title", "course_title", "status", "score", "feedback", "submitted_at", "github_url"]
        read_only_fields = fields

class AdminCertificateSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source="student.username", read_only=True)
    student_email = serializers.EmailField(source="student.email", read_only=True)
    class Meta:
        model = Certificate
        fields = ["id", "learner_name", "student_username", "student_email", "course_title", "average_score", "verification_code", "issued_at", "is_valid"]
        read_only_fields = fields

RESOURCE_CONFIG = {
 "courses": {"model":Course,"serializer":AdminCourseSerializer,"writable":True,"search":("title","slug","instructor","description"),"ordering":("title","id")},
 "modules": {"model":Module,"serializer":AdminModuleSerializer,"writable":True,"search":("title","course__title","description"),"ordering":("course__title","order","id"),"select_related":("course",)},
 "lessons": {"model":Lesson,"serializer":AdminLessonSerializer,"writable":True,"search":("title","course__title","module__title","content"),"ordering":("course__title","module__order","order","id"),"select_related":("course","module")},
 "activities": {"model":Activity,"serializer":AdminActivitySerializer,"writable":True,"search":("title","lesson__title","lesson__course__title","activity_type"),"ordering":("lesson__course__title","lesson__order","order","id"),"select_related":("lesson","lesson__course")},
 "quizzes": {"model":Quiz,"serializer":AdminQuizSerializer,"writable":True,"search":("activity__title","activity__lesson__title","activity__lesson__course__title"),"ordering":("activity__lesson__course__title","activity__lesson__order","activity__title","id"),"select_related":("activity","activity__lesson","activity__lesson__course")},
 "questions": {"model":QuizQuestion,"serializer":AdminQuizQuestionSerializer,"writable":True,"search":("question_text","quiz__activity__title","quiz__activity__lesson__course__title"),"ordering":("quiz__activity__title","order","id"),"select_related":("quiz","quiz__activity","quiz__activity__lesson","quiz__activity__lesson__course")},
 "choices": {"model":QuizChoice,"serializer":AdminQuizChoiceSerializer,"writable":True,"search":("choice_text","question__question_text","question__quiz__activity__title"),"ordering":("question__order","order","id"),"select_related":("question","question__quiz","question__quiz__activity")},
 "enrollments": {"model":Enrollment,"serializer":AdminEnrollmentSerializer,"writable":False,"search":("student__username","student__email","course__title"),"ordering":("-enrolled_at","-id"),"select_related":("student","course")},
 "submissions": {"model":Submission,"serializer":AdminSubmissionSerializer,"writable":False,"search":("student__username","activity__title","activity__lesson__course__title","status"),"ordering":("-submitted_at","-id"),"select_related":("student","activity","activity__lesson","activity__lesson__course")},
 "certificates": {"model":Certificate,"serializer":AdminCertificateSerializer,"writable":False,"search":("learner_name","student__username","student__email","course_title"),"ordering":("-issued_at","-id"),"select_related":("student","course")},
}

def _config(resource):
    return RESOURCE_CONFIG.get(resource)

def _queryset(config):
    qs = config["model"].objects.all()
    if config.get("select_related"):
        qs = qs.select_related(*config["select_related"])
    return qs.order_by(*config["ordering"])

class AdminLearningResourceAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPlatformSuperuser]
    def get(self, request, resource):
        config = _config(resource)
        if config is None: return Response({"detail":"Unknown admin learning resource."}, status=status.HTTP_404_NOT_FOUND)
        qs = _queryset(config)
        query = str(request.query_params.get("q", "")).strip()[:120]
        if query:
            expression = Q()
            for field in config["search"]: expression |= Q(**{f"{field}__icontains":query})
            qs = qs.filter(expression)
        try:
            page = max(1, int(request.query_params.get("page", "1")))
            page_size = min(100, max(1, int(request.query_params.get("page_size", "100"))))
        except (TypeError, ValueError):
            return Response({"detail":"Page and page_size must be positive integers."}, status=status.HTTP_400_BAD_REQUEST)
        count = qs.count(); pages = max(1, (count + page_size - 1)//page_size); page = min(page,pages); start=(page-1)*page_size
        data = config["serializer"](qs[start:start+page_size], many=True).data
        return Response({"count":count,"page":page,"page_size":page_size,"pages":pages,"results":data}, status=status.HTTP_200_OK)
    def post(self, request, resource):
        config = _config(resource)
        if config is None: return Response({"detail":"Unknown admin learning resource."}, status=status.HTTP_404_NOT_FOUND)
        if not config["writable"]: return Response({"detail":"This register is read-only from the admin workspace."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        serializer = config["serializer"](data=request.data); serializer.is_valid(raise_exception=True); item = serializer.save()
        return Response(config["serializer"](item).data, status=status.HTTP_201_CREATED)

class AdminLearningResourceDetailAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPlatformSuperuser]
    def get(self, request, resource, item_id):
        config = _config(resource)
        if config is None: return Response({"detail":"Unknown admin learning resource."}, status=status.HTTP_404_NOT_FOUND)
        item = get_object_or_404(_queryset(config), pk=item_id)
        return Response(config["serializer"](item).data, status=status.HTTP_200_OK)
    def patch(self, request, resource, item_id):
        config = _config(resource)
        if config is None: return Response({"detail":"Unknown admin learning resource."}, status=status.HTTP_404_NOT_FOUND)
        if not config["writable"]: return Response({"detail":"This register is read-only from the admin workspace."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        item = get_object_or_404(config["model"].objects.all(), pk=item_id)
        serializer = config["serializer"](item, data=request.data, partial=True); serializer.is_valid(raise_exception=True); item = serializer.save()
        item = get_object_or_404(_queryset(config), pk=item.pk)
        return Response(config["serializer"](item).data, status=status.HTTP_200_OK)
