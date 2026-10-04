from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.utils import timezone

import os
import subprocess
import tempfile

from .models import (
    Activity,
    ActivityCompletion,
    Course,
    Certificate,
    Enrollment,
    Lesson,
    Module,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizChoice,
    QuizQuestion,
    Submission,
    Notification,
)


User = get_user_model()


# ============================================================
# HOME
# ============================================================

def course_list(request):
    """
    Display all available courses.
    """
    courses = Course.objects.all().order_by("created_at", "title")

    return render(
        request,
        "academy/course_list.html",
        {
            "courses": courses,
        },
    )


# ============================================================
# ============================================================
# ============================================================
# COURSE DETAIL
# ============================================================

def course_detail(request, slug):
    """
    Display a course with its modules, lessons,
    enrollment status, and learner progress.
    """

    course = get_object_or_404(
        Course.objects.prefetch_related(
            "modules__lessons__activities",
            "lessons__activities",
        ),
        slug=slug,
    )

    # --------------------------------------------------------
    # CHECK ENROLLMENT
    # --------------------------------------------------------

    is_enrolled = False

    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(
            student=request.user,
            course=course,
        ).exists()

    # --------------------------------------------------------
    # GET MODULES
    # --------------------------------------------------------

    modules = list(
        course.modules.all().order_by("order")
    )

    # --------------------------------------------------------
    # GET UNASSIGNED LESSONS
    # --------------------------------------------------------

    unassigned_lessons = course.lessons.filter(
        module__isnull=True
    ).order_by("order")

    # --------------------------------------------------------
    # DEFAULT PROGRESS
    # --------------------------------------------------------

    course_progress_value = {
        "lessons_total": 0,
        "lessons_completed": 0,
        "lesson_percentage": 0,
        "activities_total": 0,
        "activities_completed": 0,
        "activity_percentage": 0,
        "average_score": None,
        "total": 0,
        "completed": 0,
        "percentage": 0,
    }

    module_progress_data = {}
    next_activity = None

    # --------------------------------------------------------
    # AUTHENTICATED LEARNER
    # --------------------------------------------------------

    if request.user.is_authenticated:

        course_progress_value = _course_progress(
            request.user,
            course,
        )

        # ----------------------------------------------------
        # MODULE PROGRESS
        # ----------------------------------------------------

        for module in modules:

            progress = _module_progress(
                request.user,
                module,
            )

            module_progress_data[module.id] = progress

            module.progress = progress.get(
                "percentage",
                0,
            )

            module.completed_lessons = progress.get(
                "completed_lessons",
                0,
            )

            module.total_lessons = progress.get(
                "total_lessons",
                module.lessons.count(),
            )

            module.is_completed = (
                module.progress == 100
            )

        # ----------------------------------------------------
        # MODULE LOCKING
        # ----------------------------------------------------

        for module in modules:

            module.is_locked = False

            if module.order == 1:
                continue

            previous_module = next(
                (
                    previous
                    for previous in modules
                    if previous.order == module.order - 1
                ),
                None,
            )

            if previous_module and not getattr(
                previous_module,
                "is_completed",
                False,
            ):
                module.is_locked = True

        # ----------------------------------------------------
        # LESSON STATUS + ACTIVITY PROGRESS
        # ----------------------------------------------------

        for module in modules:

            for lesson in module.lessons.all().order_by("order"):

                lesson.is_completed = _lesson_is_completed(
                    request.user,
                    lesson,
                )

                lesson.is_locked = not _is_lesson_unlocked(
                    request.user,
                    lesson,
                )

                required_activities = lesson.activities.filter(
                    is_required=True,
                )

                completed_ids = set(
                    ActivityCompletion.objects.filter(
                        student=request.user,
                        activity__in=required_activities,
                    ).values_list(
                        "activity_id",
                        flat=True,
                    )
                )

                lesson.total_required_activities = (
                    required_activities.count()
                )

                lesson.completed_required_activities = len(
                    completed_ids
                )

                lesson.activity_percentage = (
                    round(
                        lesson.completed_required_activities
                        / lesson.total_required_activities
                        * 100
                    )
                    if lesson.total_required_activities
                    else 100
                )

                lesson.next_activity = (
                    required_activities
                    .exclude(id__in=completed_ids)
                    .order_by("order")
                    .first()
                )

                # First available unfinished activity becomes
                # the course-level Continue Learning target.
                if (
                    next_activity is None
                    and not lesson.is_locked
                    and lesson.next_activity is not None
                ):
                    next_activity = lesson.next_activity

        # ----------------------------------------------------
        # UNASSIGNED LESSON STATUS
        # ----------------------------------------------------

        for lesson in unassigned_lessons:

            lesson.is_completed = _lesson_is_completed(
                request.user,
                lesson,
            )

            lesson.is_locked = not _is_lesson_unlocked(
                request.user,
                lesson,
            )

            required_activities = lesson.activities.filter(
                is_required=True,
            )

            completed_ids = set(
                ActivityCompletion.objects.filter(
                    student=request.user,
                    activity__in=required_activities,
                ).values_list(
                    "activity_id",
                    flat=True,
                )
            )

            lesson.total_required_activities = (
                required_activities.count()
            )

            lesson.completed_required_activities = len(
                completed_ids
            )

            lesson.activity_percentage = (
                round(
                    lesson.completed_required_activities
                    / lesson.total_required_activities
                    * 100
                )
                if lesson.total_required_activities
                else 100
            )

            lesson.next_activity = (
                required_activities
                .exclude(id__in=completed_ids)
                .order_by("order")
                .first()
            )

            if (
                next_activity is None
                and not lesson.is_locked
                and lesson.next_activity is not None
            ):
                next_activity = lesson.next_activity

    else:

        # ----------------------------------------------------
        # VISITOR DEFAULTS
        # ----------------------------------------------------

        for module in modules:

            module.progress = 0
            module.completed_lessons = 0
            module.total_lessons = module.lessons.count()
            module.is_completed = False
            module.is_locked = False

            for lesson in module.lessons.all():

                lesson.is_completed = False
                lesson.is_locked = False

                lesson.total_required_activities = (
                    lesson.activities.filter(
                        is_required=True,
                    ).count()
                )

                lesson.completed_required_activities = 0

                lesson.activity_percentage = 0

                lesson.next_activity = None

        for lesson in unassigned_lessons:

            lesson.is_completed = False
            lesson.is_locked = False

            lesson.total_required_activities = (
                lesson.activities.filter(
                    is_required=True,
                ).count()
            )

            lesson.completed_required_activities = 0
            lesson.activity_percentage = 0
            lesson.next_activity = None

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {
        "course": course,
        "modules": modules,
        "unassigned_lessons": unassigned_lessons,
        "course_progress": course_progress_value,
        "module_progress": module_progress_data,
        "is_enrolled": is_enrolled,
        "next_activity": next_activity,
    }

    return render(
        request,
        "academy/course_detail.html",
        context,
    )


# ENROLL IN COURSE
# ============================================================

@login_required
@require_http_methods(["POST"])
def enroll_course(request, slug):
    """
    Enroll the authenticated student in a course.
    """

    course = get_object_or_404(
        Course,
        slug=slug,
    )

    Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
    )

    return redirect(
        "course_detail",
        slug=course.slug,
    )


# ============================================================
# MY COURSES
# ============================================================

@login_required
def my_courses(request):
    """
    Display the authenticated student's learning dashboard.

    The dashboard combines enrolled courses, recent submissions,
    and recent notifications while keeping all data scoped to the
    currently authenticated user.
    """

    enrollments = (
        Enrollment.objects
        .filter(student=request.user)
        .select_related("course")
        .order_by("-enrolled_at")
    )

    for enrollment in enrollments:
        enrollment.progress = _course_progress(
            request.user,
            enrollment.course,
        )

        enrollment.next_activity = _next_required_activity(
            request.user,
            enrollment.course,
        )

    recent_submissions = list(
        Submission.objects
        .filter(student=request.user)
        .select_related(
            "activity",
            "activity__lesson",
            "activity__lesson__course",
        )
        .order_by("-submitted_at")[:5]
    )

    recent_notifications = list(
        Notification.objects
        .filter(recipient=request.user)
        .order_by("-created_at")[:5]
    )

    unread_notification_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).count()

    return render(
        request,
        "academy/my_courses.html",
        {
            "enrollments": enrollments,
            "recent_submissions": recent_submissions,
            "recent_notifications": recent_notifications,
            "dashboard_unread_notification_count": unread_notification_count,
        },
    )


# ============================================================
# LESSON DETAIL
# ============================================================

def lesson_detail(request, course_slug, lesson_id):
    """
    Display a lesson and its activities.
    """
    course = get_object_or_404(
        Course,
        slug=course_slug,
    )

    lesson = get_object_or_404(
        Lesson.objects.prefetch_related("activities"),
        id=lesson_id,
        course=course,
    )

    # --------------------------------------------------------
    # ENROLLMENT CHECK
    # --------------------------------------------------------

    if not request.user.is_authenticated:
        return redirect(
            f"/accounts/login/?next={request.path}"
        )

    if not _is_enrolled(
        request.user,
        course,
    ):
        return render(
            request,
            "academy/lesson_locked.html",
            {
                "course": course,
                "lesson": lesson,
                "previous_lesson": None,
                "enrollment_required": True,
            },
            status=403,
        )

    # Enforce lesson and module sequencing.
    if request.user.is_authenticated:
        if not _is_lesson_unlocked(
            request.user,
            lesson,
        ):
            previous_lesson = (
                Lesson.objects
                .filter(
                    course=course,
                    module=lesson.module,
                    order__lt=lesson.order,
                )
                .order_by("-order")
                .first()
            )

            if previous_lesson is None and lesson.module_id:
                previous_module = (
                    Module.objects
                    .filter(
                        course=course,
                        order__lt=lesson.module.order,
                    )
                    .order_by("-order")
                    .first()
                )

                if previous_module:
                    previous_lesson = (
                        Lesson.objects
                        .filter(
                            module=previous_module,
                        )
                        .order_by("-order")
                        .first()
                    )

            return render(
                request,
                "academy/lesson_locked.html",
                {
                    "course": course,
                    "lesson": lesson,
                    "previous_lesson": previous_lesson,
                },
                status=403,
            )
    activities = lesson.activities.all().order_by("order")

    completed_activity_ids = set()

    if request.user.is_authenticated:
        completed_activity_ids = set(
            ActivityCompletion.objects.filter(
                student=request.user,
                activity__lesson=lesson,
            ).values_list(
                "activity_id",
                flat=True,
            )
        )

    context = {
        "course": course,
        "lesson": lesson,
        "activities": activities,
        "completed_activity_ids": completed_activity_ids,
    }

    return render(
        request,
        "academy/lesson_detail.html",
        context,
    )


# ============================================================
# ACTIVITY DETAIL
# ============================================================

@require_http_methods(["GET", "POST"])
def activity_detail(
    request,
    course_slug,
    lesson_id,
    activity_id,
):
    """
    Display an activity and handle submissions.

    Python code execution is allowed only when DEBUG=True.
    This prevents arbitrary submitted Python code from being
    executed on a public production server.
    """

    course = get_object_or_404(
        Course,
        slug=course_slug,
    )

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        course=course,
    )

    activity = get_object_or_404(
        Activity,
        id=activity_id,
        lesson=lesson,
    )

    # --------------------------------------------------------
    # ENROLLMENT CHECK
    # --------------------------------------------------------

    if not request.user.is_authenticated:
        return redirect(
            f"/accounts/login/?next={request.path}"
        )

    if not _is_enrolled(
        request.user,
        course,
    ):
        return render(
            request,
            "academy/lesson_locked.html",
            {
                "course": course,
                "lesson": lesson,
                "previous_lesson": None,
                "enrollment_required": True,
            },
            status=403,
        )

    # --------------------------------------------------------
    # ACTIVITY / LESSON SEQUENCING CHECK
    # --------------------------------------------------------

    if not _is_activity_unlocked(
        request.user,
        activity,
    ):
        previous_lesson = (
            Lesson.objects
            .filter(
                course=course,
                module=lesson.module,
                order__lt=lesson.order,
            )
            .order_by("-order")
            .first()
        )

        if previous_lesson is None and lesson.module_id:
            previous_module = (
                Module.objects
                .filter(
                    course=course,
                    order__lt=lesson.module.order,
                )
                .order_by("-order")
                .first()
            )

            if previous_module:
                previous_lesson = (
                    Lesson.objects
                    .filter(
                        module=previous_module,
                    )
                    .order_by("-order")
                    .first()
                )

        return render(
            request,
            "academy/lesson_locked.html",
            {
                "course": course,
                "lesson": lesson,
                "previous_lesson": previous_lesson,
            },
            status=403,
        )
    submission = None
    output = None
    error = None
    code = ""
    program_input = ""
    response_text = ""
    github_url = ""

    # Sample input for the built-in input exercises.
    # This populates the Program Input box on first load.
    if activity.activity_type == "coding":
        if activity.id == 7:
            program_input = "Victor\n25"
        elif activity.id == 8:
            program_input = "Victor\n25\n1.75"
    quiz = None
    quiz_attempt = None

    is_completed = (
        request.user.is_authenticated
        and ActivityCompletion.objects.filter(
            student=request.user,
            activity=activity,
        ).exists()
    )

    if request.method == "POST":

        if not request.user.is_authenticated:
            return redirect(
                f"/accounts/login/?next={request.path}"
            )

        code = request.POST.get(
            "code",
            "",
        ).strip()

        program_input = request.POST.get(
            "program_input",
            "",
        )

        # Provide sample input for the built-in input exercises
        # when the learner leaves Program Input empty.
        if not program_input.strip() and activity.activity_type == "coding":
            if activity.id == 7:
                program_input = "Victor\n25"
            elif activity.id == 8:
                program_input = "Victor\n25\n1.75"

        response_text = request.POST.get(
            "response_text",
            "",
        ).strip()

        github_url = request.POST.get(
            "github_url",
            "",
        ).strip()

        attachment = request.FILES.get("attachment")

        submit_activity = "submit_activity" in request.POST

        # ----------------------------------------------------
        # Reading activity
        # ----------------------------------------------------

        if activity.activity_type == "reading":

            _mark_progress(request.user, activity)
            is_completed = True

            return redirect(
                "activity_detail",
                course_slug=course.slug,
                lesson_id=lesson.id,
                activity_id=activity.id,
            )

        # ----------------------------------------------------
        # Coding activity
        # ----------------------------------------------------

        elif activity.activity_type == "coding":

            if not code:
                error = "Please enter Python code before submitting."

            elif len(code) > 10000:
                error = (
                    "Code is too long. Please keep submissions under "
                    "10,000 characters."
                )

            elif len(program_input) > 5000:
                error = (
                    "Program input is too long. Please keep it under "
                    "5,000 characters."
                )

            elif not settings.DEBUG:

                if submit_activity:

                    Submission.objects.create(
                        student=request.user,
                        activity=activity,
                        code=code,
                        status="submitted",
                    )

                    output = (
                        "Code submitted successfully for instructor "
                        "assessment. Code execution is disabled in "
                        "production."
                    )

                else:

                    error = (
                        "The online code runner is unavailable in "
                        "production. You can still submit your code "
                        "for instructor assessment."
                    )

            else:

                try:

                    with tempfile.TemporaryDirectory() as temp_dir:

                        file_path = os.path.join(
                            temp_dir,
                            "solution.py",
                        )

                        with open(
                            file_path,
                            "w",
                            encoding="utf-8",
                        ) as code_file:

                            code_file.write(code)

                        result = subprocess.run(
                            [
                                "python",
                                file_path,
                            ],
                            input=program_input,
                            capture_output=True,
                            text=True,
                            timeout=5,
                            cwd=temp_dir,
                        )

                        output = result.stdout

                        if result.stderr:
                            error = result.stderr

                except subprocess.TimeoutExpired:

                    error = (
                        "Your program took too long to execute. "
                        "Execution was stopped."
                    )

                except Exception as exc:

                    error = (
                        "An error occurred while running your code: "
                        f"{exc}"
                    )

                # ------------------------------------------------
                # Save only when Submit Activity is clicked
                # ------------------------------------------------

                if submit_activity:

                    submission = Submission.objects.create(
                        student=request.user,
                        activity=activity,
                        code=code,
                        status=(
                            "error"
                            if error
                            else "submitted"
                        ),
                    )

                    if not error:
                        _mark_progress(request.user, activity)
                        is_completed = True

        # ----------------------------------------------------
        # Assignment / Lab activity
        # ----------------------------------------------------

        elif activity.activity_type in ("assignment", "lab"):

            if submit_activity:

                if len(response_text) > 20000:

                    error = (
                        "Your response is too long. "
                        "Please keep it under 20,000 characters."
                    )

                elif len(github_url) > 500:

                    error = (
                        "The GitHub URL is too long. "
                        "Please provide a valid submission URL."
                    )

                elif github_url and not github_url.startswith(
                    (
                        "https://github.com/",
                        "http://github.com/",
                    )
                ):

                    error = (
                        "Please enter a valid GitHub URL beginning with "
                        "https://github.com/"
                    )

                elif attachment and attachment.size > 10 * 1024 * 1024:

                    error = (
                        "The attachment is too large. "
                        "Please keep files under 10 MB."
                    )

                elif (
                    attachment
                    and os.path.splitext(attachment.name)[1]
                    .lower()
                    .lstrip(".")
                    not in {
                        "pdf",
                        "doc",
                        "docx",
                        "txt",
                        "zip",
                        "py",
                        "ipynb",
                        "png",
                        "jpg",
                        "jpeg",
                    }
                ):

                    error = (
                        "Unsupported attachment type. "
                        "Allowed files: PDF, DOC, DOCX, TXT, ZIP, PY, "
                        "IPYNB, PNG, JPG, and JPEG."
                    )

                elif not response_text and not github_url and not attachment:

                    error = (
                        "Please provide at least one submission item: "
                        "a written response, GitHub URL, or attachment."
                    )

                else:

                    Submission.objects.create(
                        student=request.user,
                        activity=activity,
                        code="",
                        response_text=response_text,
                        github_url=github_url,
                        attachment=attachment,
                        status="submitted",
                    )

        # ----------------------------------------------------
        # Other activity types
        # ----------------------------------------------------

        else:

            if submit_activity:

                _mark_progress(
                    request.user,
                    activity,
                )
                is_completed = True

    # --------------------------------------------------------
    # Existing submission
    # --------------------------------------------------------

    if request.user.is_authenticated and submission is None:

        submission = (
            Submission.objects
            .filter(
                student=request.user,
                activity=activity,
            )
            .order_by("-submitted_at")
            .first()
        )

    if request.method == "GET" and submission:

        response_text = submission.response_text
        github_url = submission.github_url

    latest_submission = submission

    correction_submission = (
        latest_submission
        if latest_submission and latest_submission.status == "correction"
        else None
    )

    context = {
        "course": course,
        "lesson": lesson,
        "activity": activity,
        "submission": submission,
        "latest_submission": latest_submission,
        "correction_submission": correction_submission,
        "output": output,
        "error": error,
        "code": code,
        "program_input": program_input,
        "response_text": response_text,
        "github_url": github_url,
        "is_completed": is_completed,
        "quiz": quiz,
    }

    return render(
        request,
        "academy/activity_detail.html",
        context,
    )


# ============================================================
# MARK ACTIVITY COMPLETE
# ============================================================

@login_required
def mark_activity_complete(
    request,
    course_slug,
    lesson_id,
    activity_id,
):
    """
    Mark an activity as completed.
    """

    activity = get_object_or_404(
        Activity,
        id=activity_id,
        lesson__id=lesson_id,
        lesson__course__slug=course_slug,
    )

    _mark_progress(
        request.user,
        activity,
    )

    return redirect(
        "activity_detail",
        course_slug=course_slug,
        lesson_id=lesson_id,
        activity_id=activity_id,
    )


# ============================================================
# SUBMISSION HISTORY
# ============================================================

@login_required
def submission_history(
    request,
    course_slug,
    lesson_id,
    activity_id,
):
    """
    Display the student's previous submissions for an activity.
    """

    course = get_object_or_404(
        Course,
        slug=course_slug,
    )

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        course=course,
    )

    activity = get_object_or_404(
        Activity,
        id=activity_id,
        lesson=lesson,
    )

    submissions = (
        Submission.objects
        .filter(
            student=request.user,
            activity=activity,
        )
        .order_by("-submitted_at")
    )

    return render(
        request,
        "academy/submission_history.html",
        {
            "course": course,
            "lesson": lesson,
            "activity": activity,
            "submissions": submissions,
        },
    )


# ============================================================
# SUBMISSION ATTACHMENT
# ============================================================

@login_required
def submission_attachment(request, submission_id):
    """
    Serve a submission attachment only to its owner or an
    authorized instructor/admin.
    """

    submission = get_object_or_404(
        Submission,
        id=submission_id,
    )

    is_instructor = (
        request.user.is_staff
        or getattr(request.user, "role", None) == "INSTRUCTOR"
    )

    if (
        not is_instructor
        and submission.student_id != request.user.id
    ):
        return HttpResponse(
            "You do not have permission to access this attachment.",
            status=403,
        )

    if not submission.attachment:
        return HttpResponse(
            "No attachment is available for this submission.",
            status=404,
        )

    try:
        file_handle = submission.attachment.open("rb")
    except FileNotFoundError:
        return HttpResponse(
            "The attachment could not be found.",
            status=404,
        )

    filename = os.path.basename(
        submission.attachment.name
    )

    return FileResponse(
        file_handle,
        as_attachment=True,
        filename=filename,
    )


# ============================================================


# ============================================================
# STUDENT NOTIFICATIONS
# ============================================================

@login_required
def notification_list(request):
    """
    Display notifications belonging only to the authenticated user.
    """
    notifications = (
        Notification.objects
        .filter(recipient=request.user)
        .order_by("-created_at")
    )

    return render(
        request,
        "academy/notifications.html",
        {
            "notifications": notifications,
        },
    )


@login_required
def notification_read(request, notification_id):
    """
    Mark a notification as read and redirect to its target.
    """
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user,
    )

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    if notification.link_url:
        return redirect(notification.link_url)

    return redirect("notification_list")



# ============================================================
# STUDENT ASSESSMENT HISTORY
# ============================================================

@login_required
def student_assessment_history(request):
    """
    Unified student assessment center.

    Combines coding/assignment/lab submissions with completed
    quiz attempts while keeping every record scoped to the
    authenticated student.

    Supported filters:
    - course
    - assessment type
    - assessment status
    """

    submissions_base = (
        Submission.objects
        .filter(student=request.user)
        .select_related(
            "activity",
            "activity__lesson",
            "activity__lesson__course",
        )
        .order_by("-submitted_at", "-id")
    )

    quiz_attempts_base = (
        QuizAttempt.objects
        .filter(
            student=request.user,
            completed_at__isnull=False,
        )
        .select_related(
            "quiz",
            "quiz__activity",
            "quiz__activity__lesson",
            "quiz__activity__lesson__course",
        )
        .prefetch_related(
            "quiz__questions",
        )
        .order_by("-completed_at", "-id")
    )

    # --------------------------------------------------------
    # FILTER VALUES
    # --------------------------------------------------------

    course_filter = (
        request.GET.get(
            "course",
            "all",
        )
        .strip()
    )

    type_filter = (
        request.GET.get(
            "type",
            "all",
        )
        .strip()
        .lower()
    )

    status_filter = (
        request.GET.get(
            "status",
            "all",
        )
        .strip()
        .lower()
    )

    valid_types = {
        "all",
        "submission",
        "quiz",
    }

    valid_statuses = {
        "all",
        "pending",
        "graded",
        "correction",
        "error",
        "passed",
        "not_passed",
    }

    if type_filter not in valid_types:
        type_filter = "all"

    if status_filter not in valid_statuses:
        status_filter = "all"

    # --------------------------------------------------------
    # COURSE LIST
    # --------------------------------------------------------

    courses = (
        Course.objects
        .filter(
            enrollments__student=request.user,
        )
        .distinct()
        .order_by(
            "title",
            "id",
        )
    )

    selected_course = None

    if course_filter != "all":

        selected_course = (
            courses
            .filter(
                slug=course_filter,
            )
            .first()
        )

        if selected_course is None:
            course_filter = "all"

        else:
            submissions_base = submissions_base.filter(
                activity__lesson__course=selected_course,
            )

            quiz_attempts_base = quiz_attempts_base.filter(
                quiz__activity__lesson__course=selected_course,
            )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    submission_count = submissions_base.count()
    quiz_count = quiz_attempts_base.count()

    pending_count = submissions_base.filter(
        status="submitted",
        score__isnull=True,
    ).count()

    graded_count = submissions_base.filter(
        status="graded",
        score__isnull=False,
    ).count()

    correction_count = submissions_base.filter(
        status="correction",
    ).count()

    error_count = submissions_base.filter(
        status="error",
    ).count()

    quiz_passed_count = quiz_attempts_base.filter(
        passed=True,
    ).count()

    quiz_not_passed_count = quiz_attempts_base.filter(
        passed=False,
    ).count()

    quiz_pass_rate = (
        round(
            (
                quiz_passed_count
                / quiz_count
            ) * 100,
            1,
        )
        if quiz_count
        else None
    )

    # --------------------------------------------------------
    # APPLY TYPE / STATUS FILTERS
    # --------------------------------------------------------

    submissions = submissions_base

    if type_filter == "quiz":
        submissions = submissions.none()

    elif status_filter == "pending":
        submissions = submissions.filter(
            status="submitted",
            score__isnull=True,
        )

    elif status_filter == "graded":
        submissions = submissions.filter(
            status="graded",
            score__isnull=False,
        )

    elif status_filter == "correction":
        submissions = submissions.filter(
            status="correction",
        )

    elif status_filter == "error":
        submissions = submissions.filter(
            status="error",
        )

    elif status_filter in {
        "passed",
        "not_passed",
    }:
        submissions = submissions.none()

    quiz_attempts = quiz_attempts_base

    if type_filter == "submission":
        quiz_attempts = quiz_attempts.none()

    elif status_filter == "passed":
        quiz_attempts = quiz_attempts.filter(
            passed=True,
        )

    elif status_filter == "not_passed":
        quiz_attempts = quiz_attempts.filter(
            passed=False,
        )

    elif status_filter in {
        "pending",
        "graded",
        "correction",
        "error",
    }:
        quiz_attempts = quiz_attempts.none()

    # --------------------------------------------------------
    # BUILD COMBINED ASSESSMENT LIST
    # --------------------------------------------------------

    assessments = []

    for submission in submissions:

        if submission.status == "correction":
            status_label = "Needs Correction"
            status_class = "correction-status"

        elif submission.score is not None:
            status_label = "Graded"
            status_class = "graded-status"

        elif submission.status == "error":
            status_label = "Execution Error"
            status_class = "error-status"

        else:
            status_label = "Pending Review"
            status_class = "pending-status"

        percentage = None

        if (
            submission.score is not None
            and submission.activity.max_score
        ):
            percentage = round(
                (
                    submission.score
                    / submission.activity.max_score
                ) * 100,
                1,
            )

        assessments.append(
            {
                "kind": "submission",
                "title": submission.activity.title,
                "course": submission.activity.lesson.course,
                "lesson": submission.activity.lesson,
                "submitted_at": submission.submitted_at,
                "score": submission.score,
                "max_score": submission.activity.max_score,
                "percentage": percentage,
                "status_label": status_label,
                "status_class": status_class,
                "submission": submission,
            }
        )

    for attempt in quiz_attempts:

        total_points = sum(
            question.points
            for question in attempt.quiz.questions.all()
            if question.is_active
        )

        percentage = (
            round(
                (
                    attempt.score
                    / total_points
                ) * 100,
                1,
            )
            if total_points
            else 0
        )

        if attempt.passed:
            status_label = "Quiz Passed"
            status_class = "graded-status"
        else:
            status_label = "Not Passed"
            status_class = "error-status"

        assessments.append(
            {
                "kind": "quiz",
                "title": attempt.quiz.activity.title,
                "course": attempt.quiz.activity.lesson.course,
                "lesson": attempt.quiz.activity.lesson,
                "submitted_at": (
                    attempt.completed_at
                    or attempt.created_at
                ),
                "score": attempt.score,
                "max_score": total_points,
                "percentage": percentage,
                "status_label": status_label,
                "status_class": status_class,
                "attempt": attempt,
            }
        )

    assessments.sort(
        key=lambda item: item["submitted_at"],
        reverse=True,
    )

    # --------------------------------------------------------
    # PERFORMANCE SUMMARY
    # --------------------------------------------------------

    score_percentages = []

    for submission in submissions_base:

        if (
            submission.score is not None
            and submission.activity.max_score
        ):
            score_percentages.append(
                (
                    submission.score
                    / submission.activity.max_score
                ) * 100
            )

    for attempt in quiz_attempts_base:

        total_points = sum(
            question.points
            for question in attempt.quiz.questions.all()
            if question.is_active
        )

        if total_points:
            score_percentages.append(
                (
                    attempt.score
                    / total_points
                ) * 100
            )

    average_percentage = (
        round(
            sum(score_percentages)
            / len(score_percentages),
            1,
        )
        if score_percentages
        else None
    )

    counts = {
        "all": submission_count + quiz_count,
        "submissions": submission_count,
        "quizzes": quiz_count,
        "pending": pending_count,
        "graded": graded_count,
        "correction": correction_count,
        "error": error_count,
        "quiz_passed": quiz_passed_count,
        "quiz_not_passed": quiz_not_passed_count,
    }

    return render(
        request,
        "academy/student_assessment_history.html",
        {
            "assessments": assessments,
            "courses": courses,
            "selected_course": selected_course,
            "course_filter": course_filter,
            "type_filter": type_filter,
            "status_filter": status_filter,
            "counts": counts,
            "average_percentage": average_percentage,
            "quiz_pass_rate": quiz_pass_rate,
        },
    )


# ============================================================
# STUDENT RESUBMISSION
# ============================================================

@login_required
def student_resubmit_submission(request, submission_id):
    """
    Send a student back to the activity so they can correct
    and resubmit work that was marked as needing correction.

    The submission must belong to the authenticated student.
    """

    submission = get_object_or_404(
        Submission.objects.select_related(
            "activity",
            "activity__lesson",
            "activity__lesson__course",
        ),
        id=submission_id,
        student=request.user,
    )

    # Only submissions marked as needing correction
    # should expose the resubmission workflow.
    if submission.status not in {"error", "correction"}:
        return redirect(
            "student_assessment_history"
        )

    return redirect(
        "activity_detail",
        course_slug=submission.activity.lesson.course.slug,
        lesson_id=submission.activity.lesson.id,
        activity_id=submission.activity.id,
    )


# ============================================================
# INSTRUCTOR SUBMISSIONS
# ============================================================

@login_required
def instructor_submissions(request):
    """
    Display submissions for instructor/admin review.

    Supports filtering by:
    - pending
    - graded
    - error
    - all
    """

    if not (
        request.user.is_staff
        or getattr(request.user, "role", None) == "INSTRUCTOR"
    ):
        return HttpResponse(
            "You do not have permission to access this page.",
            status=403,
        )

    status_filter = request.GET.get(
        "status",
        "all",
    ).strip().lower()

    valid_filters = {
        "all",
        "pending",
        "graded",
        "correction",
        "error",
    }

    if status_filter not in valid_filters:
        status_filter = "all"

    base_queryset = (
        Submission.objects
        .select_related(
            "student",
            "activity",
            "activity__lesson",
            "activity__lesson__course",
        )
        .order_by(
            "-submitted_at",
            "-id",
        )
    )

    pending_count = Submission.objects.filter(
        status="submitted",
        score__isnull=True,
    ).count()

    graded_count = Submission.objects.filter(
        status="graded",
        score__isnull=False,
    ).count()

    correction_count = Submission.objects.filter(
        status="correction",
    ).count()

    error_count = Submission.objects.filter(
        status="error",
    ).count()

    if status_filter == "pending":
        submissions = base_queryset.filter(
            status="submitted",
            score__isnull=True,
        )

    elif status_filter == "graded":
        submissions = base_queryset.filter(
            status="graded",
            score__isnull=False,
        )

    elif status_filter == "correction":
        submissions = base_queryset.filter(
            status="correction",
        )

    elif status_filter == "error":
        submissions = base_queryset.filter(
            status="error",
        )

    else:
        submissions = base_queryset

    return render(
        request,
        "academy/instructor_submissions.html",
        {
            "submissions": submissions,
            "status_filter": status_filter,
            "pending_count": pending_count,
            "graded_count": graded_count,
            "correction_count": correction_count,
            "error_count": error_count,
            "all_count": base_queryset.count(),
        },
    )


# ============================================================
# INSTRUCTOR ASSESSMENT CENTER
# ============================================================

@login_required
def instructor_assessment_center(request):
    """
    Unified instructor workspace for student submissions and
    completed quiz attempts.
    """

    if not (
        request.user.is_staff
        or getattr(request.user, "role", None) == "INSTRUCTOR"
    ):
        return HttpResponse(
            "You do not have permission to access this page.",
            status=403,
        )

    courses = Course.objects.all().order_by(
        "title",
        "id",
    )

    course_filter = request.GET.get(
        "course",
        "all",
    ).strip()

    selected_course = None

    if course_filter not in {"", "all"}:
        try:
            selected_course = courses.filter(
                id=int(course_filter),
            ).first()
        except (TypeError, ValueError):
            selected_course = None

    if selected_course is None:
        course_filter = "all"

    type_filter = request.GET.get(
        "type",
        "all",
    ).strip().lower()

    if type_filter not in {
        "all",
        "submission",
        "quiz",
    }:
        type_filter = "all"

    status_filter = request.GET.get(
        "status",
        "all",
    ).strip().lower()

    valid_statuses = {
        "all",
        "pending",
        "graded",
        "correction",
        "error",
        "passed",
        "not_passed",
    }

    if status_filter not in valid_statuses:
        status_filter = "all"

    submission_base = (
        Submission.objects
        .select_related(
            "student",
            "activity",
            "activity__lesson",
            "activity__lesson__course",
        )
        .order_by(
            "-submitted_at",
            "-id",
        )
    )

    quiz_base = (
        QuizAttempt.objects
        .filter(
            completed_at__isnull=False,
        )
        .select_related(
            "student",
            "quiz",
            "quiz__activity",
            "quiz__activity__lesson",
            "quiz__activity__lesson__course",
        )
        .order_by(
            "-completed_at",
            "-id",
        )
    )

    if selected_course is not None:

        submission_base = submission_base.filter(
            activity__lesson__course=selected_course,
        )

        quiz_base = quiz_base.filter(
            quiz__activity__lesson__course=selected_course,
        )

    pending_count = submission_base.filter(
        status="submitted",
        score__isnull=True,
    ).count()

    graded_count = submission_base.filter(
        status="graded",
        score__isnull=False,
    ).count()

    correction_count = submission_base.filter(
        status="correction",
    ).count()

    error_count = submission_base.filter(
        status="error",
    ).count()

    quiz_passed_count = quiz_base.filter(
        passed=True,
    ).count()

    quiz_not_passed_count = quiz_base.filter(
        passed=False,
    ).count()

    all_count = (
        submission_base.count()
        + quiz_base.count()
    )

    score_percentages = []

    for submission in submission_base.filter(
        status="graded",
        score__isnull=False,
    ):

        max_score = submission.activity.max_score or 0

        if max_score > 0:
            score_percentages.append(
                (
                    float(submission.score)
                    / float(max_score)
                ) * 100
            )

    for attempt in quiz_base:

        total_points = sum(
            question.points
            for question in attempt.quiz.questions.all()
            if question.is_active
        )

        if total_points and attempt.score is not None:
            score_percentages.append(
                (
                    float(attempt.score)
                    / float(total_points)
                ) * 100
            )

    average_percentage = (
        round(
            sum(score_percentages)
            / len(score_percentages),
            1,
        )
        if score_percentages
        else None
    )

    submissions = submission_base
    quiz_attempts = quiz_base

    if type_filter == "submission":
        quiz_attempts = quiz_attempts.none()

    elif type_filter == "quiz":
        submissions = submissions.none()

    if status_filter == "pending":

        submissions = submissions.filter(
            status="submitted",
            score__isnull=True,
        )

        quiz_attempts = quiz_attempts.none()

    elif status_filter == "graded":

        submissions = submissions.filter(
            status="graded",
            score__isnull=False,
        )

        quiz_attempts = quiz_attempts.none()

    elif status_filter == "correction":

        submissions = submissions.filter(
            status="correction",
        )

        quiz_attempts = quiz_attempts.none()

    elif status_filter == "error":

        submissions = submissions.filter(
            status="error",
        )

        quiz_attempts = quiz_attempts.none()

    elif status_filter == "passed":

        submissions = submissions.none()

        quiz_attempts = quiz_attempts.filter(
            passed=True,
        )

    elif status_filter == "not_passed":

        submissions = submissions.none()

        quiz_attempts = quiz_attempts.filter(
            passed=False,
        )

    assessments = []

    for submission in submissions:

        percentage = None

        if (
            submission.score is not None
            and submission.activity.max_score
        ):

            percentage = round(
                (
                    float(submission.score)
                    / float(submission.activity.max_score)
                ) * 100,
                1,
            )

        if submission.status == "correction":

            status_label = "Needs Correction"
            status_class = "correction"

        elif submission.status == "error":

            status_label = "Execution Error"
            status_class = "error"

        elif (
            submission.status == "graded"
            and submission.score is not None
        ):

            status_label = "Graded"
            status_class = "graded"

        else:

            status_label = "Pending Review"
            status_class = "pending"

        assessments.append(
            {
                "kind": "submission",
                "student": submission.student,
                "course": submission.activity.lesson.course,
                "lesson": submission.activity.lesson,
                "title": submission.activity.title,
                "activity_type": (
                    submission.activity
                    .get_activity_type_display()
                ),
                "submitted_at": submission.submitted_at,
                "score": submission.score,
                "max_score": submission.activity.max_score,
                "percentage": percentage,
                "status_label": status_label,
                "status_class": status_class,
                "review_url": reverse(
                    "review_submission",
                    args=[submission.id],
                ),
                "target_url": reverse(
                    "activity_detail",
                    args=[
                        submission.activity.lesson.course.slug,
                        submission.activity.lesson.id,
                        submission.activity.id,
                    ],
                ),
            }
        )

    for attempt in quiz_attempts:

        total_points = sum(
            question.points
            for question in attempt.quiz.questions.all()
            if question.is_active
        )

        percentage = (
            round(
                (
                    float(attempt.score)
                    / float(total_points)
                ) * 100,
                1,
            )
            if (
                total_points
                and attempt.score is not None
            )
            else None
        )

        if attempt.passed:

            status_label = "Quiz Passed"
            status_class = "passed"

        else:

            status_label = "Quiz Not Passed"
            status_class = "not-passed"

        quiz_url = reverse(
            "instructor_quiz_edit",
            args=[attempt.quiz.id],
        )

        assessments.append(
            {
                "kind": "quiz",
                "student": attempt.student,
                "course": (
                    attempt.quiz
                    .activity
                    .lesson
                    .course
                ),
                "lesson": (
                    attempt.quiz
                    .activity
                    .lesson
                ),
                "title": (
                    attempt.quiz
                    .activity
                    .title
                ),
                "activity_type": "Quiz",
                "submitted_at": (
                    attempt.completed_at
                    or attempt.created_at
                ),
                "score": attempt.score,
                "max_score": total_points,
                "percentage": percentage,
                "status_label": status_label,
                "status_class": status_class,
                "review_url": quiz_url,
                "target_url": quiz_url,
            }
        )

    assessments.sort(
        key=lambda item: item["submitted_at"],
        reverse=True,
    )

    center_url = reverse(
        "instructor_assessment_center"
    )

    def filter_url(
        next_type="all",
        next_status="all",
    ):

        params = []

        if course_filter != "all":

            params.append(
                f"course={course_filter}"
            )

        if next_type != "all":

            params.append(
                f"type={next_type}"
            )

        if next_status != "all":

            params.append(
                f"status={next_status}"
            )

        if params:

            return (
                f"{center_url}?{'&'.join(params)}"
            )

        return center_url

    type_filter_urls = {
        "all": filter_url(
            "all",
            status_filter,
        ),
        "submission": filter_url(
            "submission",
            status_filter,
        ),
        "quiz": filter_url(
            "quiz",
            status_filter,
        ),
    }

    status_filter_urls = {
        "all": filter_url(
            type_filter,
            "all",
        ),
        "pending": filter_url(
            type_filter,
            "pending",
        ),
        "graded": filter_url(
            type_filter,
            "graded",
        ),
        "correction": filter_url(
            type_filter,
            "correction",
        ),
        "error": filter_url(
            type_filter,
            "error",
        ),
        "passed": filter_url(
            type_filter,
            "passed",
        ),
        "not_passed": filter_url(
            type_filter,
            "not_passed",
        ),
    }

    return render(
        request,
        "academy/instructor_assessment_center.html",
        {
            "assessments": assessments,
            "courses": courses,
            "selected_course": selected_course,
            "course_filter": course_filter,
            "type_filter": type_filter,
            "status_filter": status_filter,
            "type_filter_urls": type_filter_urls,
            "status_filter_urls": status_filter_urls,
            "all_count": all_count,
            "pending_count": pending_count,
            "graded_count": graded_count,
            "correction_count": correction_count,
            "error_count": error_count,
            "quiz_passed_count": quiz_passed_count,
            "quiz_not_passed_count": quiz_not_passed_count,
            "average_percentage": average_percentage,
        },
    )


# REVIEW SUBMISSION
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def review_submission(
    request,
    submission_id,
):
    """
    Allow an instructor/admin to review and grade a submission.
    """

    if not (request.user.is_staff or request.user.role == "INSTRUCTOR"):
        return HttpResponse(
            "You do not have permission to access this page.",
            status=403,
        )

    submission = get_object_or_404(
        Submission.objects.select_related(
            "student",
            "activity",
            "activity__lesson",
            "activity__lesson__course",
        ),
        id=submission_id,
    )

    error = None

    if request.method == "POST":

        score_value = request.POST.get(
            "score",
            ""
        ).strip()

        feedback = request.POST.get(
            "feedback",
            ""
        ).strip()

        status = request.POST.get(
            "status",
            "graded"
        ).strip() or "graded"

        if status not in {
            "graded",
            "correction",
        }:
            status = "graded"

        # --------------------------------------------
        # Validate score
        # --------------------------------------------

        if score_value:

            try:
                score = int(score_value)

                if score < 0:
                    raise ValueError

                if score > submission.activity.max_score:
                    raise ValueError

            except ValueError:

                error = (
                    f"Score must be between 0 and "
                    f"{submission.activity.max_score}."
                )

                return render(
                    request,
                    "academy/review_submission.html",
                    {
                        "submission": submission,
                        "error": error,
                    },
                )

            submission.score = score

        else:
            submission.score = None

        submission.feedback = feedback
        submission.status = status
        submission.save()

        # --------------------------------------------
        # Create student notification
        # --------------------------------------------

        activity_url = reverse(
            "activity_detail",
            args=[
                submission.activity.lesson.course.slug,
                submission.activity.lesson.id,
                submission.activity.id,
            ],
        )

        if submission.status == "correction":

            notification_title = "Correction Required"

            notification_message = (
                f"Your submission for "
                f"'{submission.activity.title}' needs correction."
            )

        else:

            notification_title = "Submission Graded"

            notification_message = (
                f"Your submission for "
                f"'{submission.activity.title}' has been graded."
            )

        if feedback:
            notification_message += (
                f" Instructor feedback: {feedback}"
            )

        Notification.objects.create(
            recipient=submission.student,
            notification_type=submission.status,
            title=notification_title,
            message=notification_message,
            link_url=activity_url,
        )

        # --------------------------------------------
        # Update activity completion
        # --------------------------------------------

        if submission.status == "correction":

            ActivityCompletion.objects.filter(
                student=submission.student,
                activity=submission.activity,
            ).delete()

        elif (
            submission.score is not None
            and submission.score >= 0
        ):
            _mark_progress(
                submission.student,
                submission.activity,
            )

        return redirect(
            "instructor_submissions"
        )

    return render(
        request,
        "academy/review_submission.html",
        {
            "submission": submission,
            "error": error,
        },
    )


# ============================================================
# COURSE PROGRESS
# ============================================================


# =========================================================
# QUIZ
# =========================================================

@login_required

# ============================================================
# INSTRUCTOR DASHBOARD
# ============================================================

@login_required
def instructor_dashboard(request):
    """
    Instructor/staff landing page.

    Provides a single entry point for course content,
    quiz management and submission review.
    """

    if not (
        request.user.is_staff
        or getattr(request.user, "role", None) == "INSTRUCTOR"
    ):
        return HttpResponse(
            "You do not have permission to access this page.",
            status=403,
        )

    courses = Course.objects.all().order_by(
        "title",
        "id",
    )

    modules_count = Module.objects.count()
    lessons_count = Lesson.objects.count()
    activities_count = Activity.objects.count()
    quizzes_count = Quiz.objects.count()

    pending_submissions_count = Submission.objects.filter(
        status="submitted",
        score__isnull=True,
    ).count()

    graded_submissions = list(
        Submission.objects
        .filter(
            score__isnull=False,
        )
        .select_related(
            "activity",
        )
    )

    graded_submission_percentages = []

    for submission in graded_submissions:
        max_score = submission.activity.max_score or 0

        if max_score > 0:
            percentage = (
                float(submission.score)
                / float(max_score)
            ) * 100

            graded_submission_percentages.append(
                percentage
            )

    submission_average_percentage = (
        round(
            sum(graded_submission_percentages)
            / len(graded_submission_percentages),
            1,
        )
        if graded_submission_percentages
        else None
    )

    total_students_count = User.objects.filter(
        role="STUDENT",
    ).count()

    completed_quiz_attempts_count = QuizAttempt.objects.filter(
        completed_at__isnull=False,
    ).count()

    passed_quiz_attempts_count = QuizAttempt.objects.filter(
        completed_at__isnull=False,
        passed=True,
    ).count()

    recent_submissions = list(
        Submission.objects
        .select_related(
            "student",
            "activity",
            "activity__lesson",
            "activity__lesson__course",
        )
        .order_by(
            "-submitted_at",
            "-id",
        )[:8]
    )

    recent_quiz_attempts = list(
        QuizAttempt.objects
        .filter(
            completed_at__isnull=False,
        )
        .select_related(
            "student",
            "quiz",
            "quiz__activity",
            "quiz__activity__lesson",
            "quiz__activity__lesson__course",
        )
        .order_by(
            "-completed_at",
            "-id",
        )[:8]
    )

    return render(
        request,
        "academy/instructor_dashboard.html",
        {
            "courses": courses,
            "course_count": courses.count(),
            "modules_count": modules_count,
            "lessons_count": lessons_count,
            "activities_count": activities_count,
            "quizzes_count": quizzes_count,
            "pending_submissions_count": pending_submissions_count,
            "total_students_count": total_students_count,
            "graded_submissions_count": len(
                graded_submissions
            ),
            "submission_average_percentage": (
                submission_average_percentage
            ),
            "completed_quiz_attempts_count": (
                completed_quiz_attempts_count
            ),
            "passed_quiz_attempts_count": (
                passed_quiz_attempts_count
            ),
            "recent_submissions": recent_submissions,
            "recent_quiz_attempts": recent_quiz_attempts,
        },
    )
def instructor_content_management(request):
    """
    Display all courses for instructor content management.
    """

    if not (
        request.user.is_staff
        or getattr(request.user, "role", None) == "INSTRUCTOR"
    ):
        return HttpResponse(
            "You do not have permission to access this page.",
            status=403,
        )

    courses = list(
        Course.objects
        .prefetch_related(
            "modules__lessons__activities",
        )
        .order_by(
            "title",
            "id",
        )
    )

    course_data = []

    for course in courses:

        modules = list(
            course.modules.all()
            .order_by(
                "order",
                "id",
            )
        )

        course_data.append(
            {
                "course": course,
                "module_count": len(modules),
                "lesson_count": sum(
                    module.lessons.count()
                    for module in modules
                ),
                "activity_count": sum(
                    lesson.activities.count()
                    for module in modules
                    for lesson in module.lessons.all()
                ),
            }
        )

    return render(
        request,
        "academy/instructor_content_management.html",
        {
            "course_data": course_data,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def instructor_course_content(request, course_id):
    """
    Manage the structure of one course.

    Instructors can create and edit modules, lessons,
    and activities. Existing content is not deleted here
    to protect student submissions and progress records.
    """

    if not (
        request.user.is_staff
        or getattr(request.user, "role", None) == "INSTRUCTOR"
    ):
        return HttpResponse(
            "You do not have permission to access this page.",
            status=403,
        )

    course = get_object_or_404(
        Course,
        id=course_id,
    )

    error = None

    if request.method == "POST":

        action = request.POST.get(
            "action",
            "",
        )

        # ====================================================
        # ADD MODULE
        # ====================================================

        if action == "add_module":

            title = request.POST.get(
                "title",
                "",
            ).strip()

            description = request.POST.get(
                "description",
                "",
            ).strip()

            try:
                order = int(
                    request.POST.get(
                        "order",
                        "1",
                    )
                )

                if order < 1:
                    raise ValueError

            except (TypeError, ValueError):

                error = (
                    "Module order must be a positive whole number."
                )

            if not title:
                error = "Module title is required."

            if error is None:

                Module.objects.create(
                    course=course,
                    title=title,
                    description=description,
                    order=order,
                )

                return redirect(
                    "instructor_course_content",
                    course_id=course.id,
                )

        # ====================================================
        # EDIT MODULE
        # ====================================================

        elif action == "edit_module":

            module_id = request.POST.get(
                "module_id"
            )

            module = get_object_or_404(
                Module,
                id=module_id,
                course=course,
            )

            title = request.POST.get(
                "title",
                "",
            ).strip()

            description = request.POST.get(
                "description",
                "",
            ).strip()

            try:
                order = int(
                    request.POST.get(
                        "order",
                        str(module.order),
                    )
                )

                if order < 1:
                    raise ValueError

            except (TypeError, ValueError):

                error = (
                    "Module order must be a positive whole number."
                )

            if not title:
                error = "Module title is required."

            if error is None:

                module.title = title
                module.description = description
                module.order = order
                module.save()

                return redirect(
                    "instructor_course_content",
                    course_id=course.id,
                )

        # ====================================================
        # ADD LESSON
        # ====================================================

        elif action == "add_lesson":

            module_id = request.POST.get(
                "module_id"
            )

            module = get_object_or_404(
                Module,
                id=module_id,
                course=course,
            )

            title = request.POST.get(
                "title",
                "",
            ).strip()

            content = request.POST.get(
                "content",
                "",
            ).strip()

            try:
                order = int(
                    request.POST.get(
                        "order",
                        "1",
                    )
                )

                if order < 1:
                    raise ValueError

            except (TypeError, ValueError):

                error = (
                    "Lesson order must be a positive whole number."
                )

            if not title:
                error = "Lesson title is required."

            if error is None:

                Lesson.objects.create(
                    course=course,
                    module=module,
                    title=title,
                    content=content,
                    order=order,
                )

                return redirect(
                    "instructor_course_content",
                    course_id=course.id,
                )

        # ====================================================
        # EDIT LESSON
        # ====================================================

        elif action == "edit_lesson":

            lesson_id = request.POST.get(
                "lesson_id"
            )

            lesson = get_object_or_404(
                Lesson,
                id=lesson_id,
                course=course,
            )

            module_id = request.POST.get(
                "module_id"
            )

            module = get_object_or_404(
                Module,
                id=module_id,
                course=course,
            )

            title = request.POST.get(
                "title",
                "",
            ).strip()

            content = request.POST.get(
                "content",
                "",
            ).strip()

            try:
                order = int(
                    request.POST.get(
                        "order",
                        str(lesson.order),
                    )
                )

                if order < 1:
                    raise ValueError

            except (TypeError, ValueError):

                error = (
                    "Lesson order must be a positive whole number."
                )

            if not title:
                error = "Lesson title is required."

            if error is None:

                lesson.module = module
                lesson.title = title
                lesson.content = content
                lesson.order = order
                lesson.save()

                return redirect(
                    "instructor_course_content",
                    course_id=course.id,
                )

        # ====================================================
        # ADD ACTIVITY
        # ====================================================

        elif action == "add_activity":

            lesson_id = request.POST.get(
                "lesson_id"
            )

            lesson = get_object_or_404(
                Lesson,
                id=lesson_id,
                course=course,
            )

            title = request.POST.get(
                "title",
                "",
            ).strip()

            instructions = request.POST.get(
                "instructions",
                "",
            ).strip()

            activity_type = request.POST.get(
                "activity_type",
                "",
            ).strip()

            allowed_types = dict(
                Activity._meta.get_field(
                    "activity_type"
                ).choices
            )

            if not allowed_types:

                allowed_types = {
                    "reading": "Reading",
                    "coding": "Coding",
                    "quiz": "Quiz",
                    "assignment": "Assignment",
                    "lab": "Lab",
                }

            if activity_type not in allowed_types:
                error = "Select a valid activity type."

            try:
                order = int(
                    request.POST.get(
                        "order",
                        "1",
                    )
                )

                max_score = int(
                    request.POST.get(
                        "max_score",
                        "0",
                    )
                )

                if order < 1 or max_score < 0:
                    raise ValueError

            except (TypeError, ValueError):

                error = (
                    "Order must be positive and maximum score "
                    "must be non-negative."
                )

            if not title:
                error = "Activity title is required."

            if error is None:

                is_required = (
                    request.POST.get(
                        "is_required"
                    )
                    == "on"
                )

                activity = Activity.objects.create(
                    lesson=lesson,
                    title=title,
                    activity_type=activity_type,
                    instructions=instructions,
                    order=order,
                    max_score=max_score,
                    is_required=is_required,
                )

                if activity_type == "quiz":

                    Quiz.objects.get_or_create(
                        activity=activity,
                        defaults={
                            "passing_score": 50,
                        },
                    )

                return redirect(
                    "instructor_course_content",
                    course_id=course.id,
                )

        # ====================================================
        # EDIT ACTIVITY
        # ====================================================

        elif action == "edit_activity":

            activity_id = request.POST.get(
                "activity_id"
            )

            activity = get_object_or_404(
                Activity,
                id=activity_id,
                lesson__course=course,
            )

            lesson_id = request.POST.get(
                "lesson_id"
            )

            lesson = get_object_or_404(
                Lesson,
                id=lesson_id,
                course=course,
            )

            title = request.POST.get(
                "title",
                "",
            ).strip()

            instructions = request.POST.get(
                "instructions",
                "",
            ).strip()

            activity_type = request.POST.get(
                "activity_type",
                "",
            ).strip()

            allowed_types = dict(
                Activity._meta.get_field(
                    "activity_type"
                ).choices
            )

            if not allowed_types:

                allowed_types = {
                    "reading": "Reading",
                    "coding": "Coding",
                    "quiz": "Quiz",
                    "assignment": "Assignment",
                    "lab": "Lab",
                }

            if activity_type not in allowed_types:
                error = "Select a valid activity type."

            try:
                order = int(
                    request.POST.get(
                        "order",
                        str(activity.order),
                    )
                )

                max_score = int(
                    request.POST.get(
                        "max_score",
                        str(activity.max_score),
                    )
                )

                if order < 1 or max_score < 0:
                    raise ValueError

            except (TypeError, ValueError):

                error = (
                    "Order must be positive and maximum score "
                    "must be non-negative."
                )

            if not title:
                error = "Activity title is required."

            if error is None:

                activity.lesson = lesson
                activity.title = title
                activity.instructions = instructions
                activity.activity_type = activity_type
                activity.order = order
                activity.max_score = max_score
                activity.is_required = (
                    request.POST.get(
                        "is_required"
                    )
                    == "on"
                )

                activity.save()

                if activity_type == "quiz":

                    Quiz.objects.get_or_create(
                        activity=activity,
                        defaults={
                            "passing_score": 50,
                        },
                    )

                return redirect(
                    "instructor_course_content",
                    course_id=course.id,
                )

    modules = list(
        course.modules
        .prefetch_related(
            "lessons__activities",
        )
        .order_by(
            "order",
            "id",
        )
    )

    all_lessons = list(
        Lesson.objects
        .filter(course=course)
        .select_related("module")
        .prefetch_related("activities")
        .order_by(
            "module__order",
            "order",
            "id",
        )
    )

    activity_type_choices = (
        Activity._meta
        .get_field("activity_type")
        .choices
    )

    if not activity_type_choices:

        activity_type_choices = (
            ("reading", "Reading"),
            ("coding", "Coding"),
            ("quiz", "Quiz"),
            ("assignment", "Assignment"),
            ("lab", "Lab"),
        )

    return render(
        request,
        "academy/instructor_course_content.html",
        {
            "course": course,
            "modules": modules,
            "lessons": all_lessons,
            "activity_type_choices": activity_type_choices,
            "error": error,
        },
    )


@login_required
def instructor_quizzes(request):
    """
    Display quizzes for instructor/staff management.
    """

    if not (
        request.user.is_staff
        or getattr(request.user, "role", None) == "INSTRUCTOR"
    ):
        return HttpResponse(
            "You do not have permission to access this page.",
            status=403,
        )

    quizzes = list(
        Quiz.objects
        .select_related(
            "activity",
            "activity__lesson",
            "activity__lesson__course",
        )
        .prefetch_related(
            "questions",
        )
        .order_by(
            "activity__lesson__course__title",
            "activity__lesson__order",
            "activity__order",
            "activity__title",
        )
    )

    quiz_data = []

    for quiz in quizzes:
        active_questions = [
            question
            for question in quiz.questions.all()
            if question.is_active
        ]

        quiz_data.append(
            {
                "quiz": quiz,
                "course": quiz.activity.lesson.course,
                "lesson": quiz.activity.lesson,
                "question_count": len(active_questions),
                "total_points": sum(
                    question.points
                    for question in active_questions
                ),
            }
        )

    return render(
        request,
        "academy/instructor_quiz_management.html",
        {
            "quiz_data": quiz_data,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def instructor_quiz_edit(request, quiz_id):
    """
    Create and manage quiz questions and choices.
    """

    if not (
        request.user.is_staff
        or getattr(request.user, "role", None) == "INSTRUCTOR"
    ):
        return HttpResponse(
            "You do not have permission to access this page.",
            status=403,
        )

    quiz = get_object_or_404(
        Quiz.objects.select_related(
            "activity",
            "activity__lesson",
            "activity__lesson__course",
        ),
        id=quiz_id,
    )

    error = None

    if request.method == "POST":

        action = request.POST.get(
            "action",
            "",
        )

        # ----------------------------------------------------
        # UPDATE QUIZ SETTINGS
        # ----------------------------------------------------

        if action == "update_quiz":

            try:
                passing_score = int(
                    request.POST.get(
                        "passing_score",
                        "",
                    )
                )

                if not 0 <= passing_score <= 100:
                    raise ValueError

            except (TypeError, ValueError):

                error = (
                    "Passing score must be a whole number "
                    "between 0 and 100."
                )

            else:

                quiz.passing_score = passing_score
                quiz.save(
                    update_fields=["passing_score"]
                )

                return redirect(
                    "instructor_quiz_edit",
                    quiz_id=quiz.id,
                )

        # ----------------------------------------------------
        # ADD QUESTION
        # ----------------------------------------------------

        elif action == "add_question":

            question_text = request.POST.get(
                "question_text",
                "",
            ).strip()

            if not question_text:
                error = "Question text is required."

            else:

                try:
                    points = int(
                        request.POST.get(
                            "points",
                            "10",
                        )
                    )

                    if points < 0:
                        raise ValueError

                except (TypeError, ValueError):

                    error = (
                        "Question points must be a "
                        "non-negative whole number."
                    )

                if error is None:

                    last_question = (
                        quiz.questions
                        .order_by(
                            "-order",
                            "-id",
                        )
                        .first()
                    )

                    next_order = (
                        last_question.order + 1
                        if last_question
                        else 1
                    )

                    QuizQuestion.objects.create(
                        quiz=quiz,
                        question_text=question_text,
                        order=next_order,
                        points=points,
                        is_active=True,
                    )

                    # Keep the activity maximum score synchronized.
                    quiz.activity.max_score = sum(
                        question.points
                        for question in quiz.questions.filter(
                            is_active=True
                        )
                    )
                    quiz.activity.save(
                        update_fields=["max_score"]
                    )

                    return redirect(
                        "instructor_quiz_edit",
                        quiz_id=quiz.id,
                    )

        # ----------------------------------------------------
        # UPDATE QUESTION
        # ----------------------------------------------------

        elif action == "update_question":

            question_id = request.POST.get(
                "question_id"
            )

            question = get_object_or_404(
                QuizQuestion,
                id=question_id,
                quiz=quiz,
            )

            question_text = request.POST.get(
                "question_text",
                "",
            ).strip()

            if not question_text:
                error = "Question text is required."

            else:

                try:
                    points = int(
                        request.POST.get(
                            "points",
                            str(question.points),
                        )
                    )

                    order = int(
                        request.POST.get(
                            "order",
                            str(question.order),
                        )
                    )

                    if points < 0 or order < 1:
                        raise ValueError

                except (TypeError, ValueError):

                    error = (
                        "Points must be non-negative and "
                        "order must be at least 1."
                    )

                if error is None:

                    question.question_text = question_text
                    question.points = points
                    question.order = order
                    question.is_active = (
                        request.POST.get(
                            "is_active"
                        )
                        == "on"
                    )

                    question.save()

                    # Keep the activity maximum score synchronized.
                    quiz.activity.max_score = sum(
                        item.points
                        for item in quiz.questions.filter(
                            is_active=True
                        )
                    )
                    quiz.activity.save(
                        update_fields=["max_score"]
                    )

                    return redirect(
                        "instructor_quiz_edit",
                        quiz_id=quiz.id,
                    )

        # ----------------------------------------------------
        # DELETE QUESTION
        # ----------------------------------------------------

        elif action == "delete_question":

            question_id = request.POST.get(
                "question_id"
            )

            question = get_object_or_404(
                QuizQuestion,
                id=question_id,
                quiz=quiz,
            )

            question.delete()

            quiz.activity.max_score = sum(
                question.points
                for question in quiz.questions.filter(
                    is_active=True
                )
            )

            quiz.activity.save(
                update_fields=["max_score"]
            )

            return redirect(
                "instructor_quiz_edit",
                quiz_id=quiz.id,
            )

        # ----------------------------------------------------
        # ADD CHOICE
        # ----------------------------------------------------

        elif action == "add_choice":

            question_id = request.POST.get(
                "question_id"
            )

            question = get_object_or_404(
                QuizQuestion,
                id=question_id,
                quiz=quiz,
            )

            choice_text = request.POST.get(
                "choice_text",
                "",
            ).strip()

            if not choice_text:

                error = "Choice text is required."

            else:

                last_choice = (
                    question.choices
                    .order_by(
                        "-order",
                        "-id",
                    )
                    .first()
                )

                next_order = (
                    last_choice.order + 1
                    if last_choice
                    else 1
                )

                is_correct = (
                    request.POST.get(
                        "is_correct"
                    )
                    == "on"
                )

                if is_correct:

                    question.choices.exclude(
                        id=None
                    ).update(
                        is_correct=False
                    )

                QuizChoice.objects.create(
                    question=question,
                    choice_text=choice_text,
                    is_correct=is_correct,
                    order=next_order,
                )

                return redirect(
                    "instructor_quiz_edit",
                    quiz_id=quiz.id,
                )

        # ----------------------------------------------------
        # UPDATE CHOICE
        # ----------------------------------------------------

        elif action == "update_choice":

            choice_id = request.POST.get(
                "choice_id"
            )

            choice = get_object_or_404(
                QuizChoice,
                id=choice_id,
                question__quiz=quiz,
            )

            choice_text = request.POST.get(
                "choice_text",
                "",
            ).strip()

            if not choice_text:

                error = "Choice text is required."

            else:

                is_correct = (
                    request.POST.get(
                        "is_correct"
                    )
                    == "on"
                )

                if is_correct:

                    QuizChoice.objects.filter(
                        question=choice.question
                    ).exclude(
                        id=choice.id
                    ).update(
                        is_correct=False
                    )

                choice.choice_text = choice_text
                choice.order = int(
                    request.POST.get(
                        "order",
                        choice.order,
                    )
                    or choice.order
                )
                choice.is_correct = is_correct
                choice.save()

                return redirect(
                    "instructor_quiz_edit",
                    quiz_id=quiz.id,
                )

        # ----------------------------------------------------
        # DELETE CHOICE
        # ----------------------------------------------------

        elif action == "delete_choice":

            choice_id = request.POST.get(
                "choice_id"
            )

            choice = get_object_or_404(
                QuizChoice,
                id=choice_id,
                question__quiz=quiz,
            )

            choice.delete()

            return redirect(
                "instructor_quiz_edit",
                quiz_id=quiz.id,
            )

    quiz_questions = list(
        quiz.questions
        .all()
        .order_by(
            "order",
            "id",
        )
        .prefetch_related("choices")
    )

    active_total_points = sum(
        question.points
        for question in quiz_questions
        if question.is_active
    )

    if (
        quiz.activity.max_score
        != active_total_points
    ):
        quiz.activity.max_score = active_total_points
        quiz.activity.save(
            update_fields=["max_score"]
        )

    # --------------------------------------------------------
    # QUIZ READINESS VALIDATION
    # --------------------------------------------------------

    validation_errors = []

    active_questions = [
        question
        for question in quiz_questions
        if question.is_active
    ]

    if not active_questions:
        validation_errors.append(
            "The quiz has no active questions."
        )

    for question in active_questions:

        choices = list(
            question.choices.all()
        )

        correct_count = sum(
            1
            for choice in choices
            if choice.is_correct
        )

        if not choices:
            validation_errors.append(
                f"Question {question.order} has no choices."
            )

        elif correct_count != 1:
            validation_errors.append(
                f"Question {question.order} must have exactly "
                f"one correct answer."
            )

    quiz_ready = (
        len(validation_errors) == 0
    )

    return render(
        request,
        "academy/instructor_quiz_edit.html",
        {
            "quiz": quiz,
            "course": quiz.activity.lesson.course,
            "lesson": quiz.activity.lesson,
            "questions": quiz_questions,
            "error": error,
            "validation_errors": validation_errors,
            "quiz_ready": quiz_ready,
        },
    )


@login_required
def quiz_take(
    request,
    course_slug,
    lesson_id,
    activity_id,
):
    """
    Display and automatically grade a quiz.
    """

    course = get_object_or_404(
        Course,
        slug=course_slug,
    )

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        course=course,
    )

    activity = get_object_or_404(
        Activity,
        id=activity_id,
        lesson=lesson,
        activity_type="quiz",
    )

    if not _is_enrolled(
        request.user,
        course,
    ):
        return render(
            request,
            "academy/lesson_locked.html",
            {
                "course": course,
                "lesson": lesson,
                "previous_lesson": None,
                "enrollment_required": True,
            },
            status=403,
        )

    if not _is_activity_unlocked(
        request.user,
        activity,
    ):
        return render(
            request,
            "academy/lesson_locked.html",
            {
                "course": course,
                "lesson": lesson,
                "previous_lesson": None,
            },
            status=403,
        )

    quiz = get_object_or_404(
        Quiz.objects.prefetch_related(
            "questions__choices",
        ),
        activity=activity,
    )

    questions = list(
        quiz.questions.filter(
            is_active=True,
        ).order_by(
            "order",
            "id",
        )
    )

    result = None
    attempt = None

    # -----------------------------------------------------
    # SUBMIT QUIZ
    # -----------------------------------------------------

    if request.method == "POST":

        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            student=request.user,
            score=0,
            passed=False,
            completed_at=timezone.now(),
        )

        total_points = sum(
            question.points
            for question in questions
        )

        earned_points = 0

        for question in questions:

            choice_id = request.POST.get(
                f"question_{question.id}"
            )

            if not choice_id:
                continue

            selected_choice = (
                QuizChoice.objects.filter(
                    id=choice_id,
                    question=question,
                ).first()
            )

            if selected_choice is None:
                continue

            is_correct = (
                selected_choice.is_correct
            )

            points_awarded = (
                question.points
                if is_correct
                else 0
            )

            earned_points += points_awarded

            QuizAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_choice=selected_choice,
                is_correct=is_correct,
                points_awarded=points_awarded,
            )

        if total_points > 0:

            percentage = round(
                (
                    earned_points
                    / total_points
                ) * 100
            )

        else:

            percentage = 0

        passed = (
            total_points > 0
            and percentage >= quiz.passing_score
        )

        attempt.score = earned_points
        attempt.passed = passed
        attempt.completed_at = timezone.now()

        attempt.save(
            update_fields=[
                "score",
                "passed",
                "completed_at",
            ]
        )

        if passed:

            _mark_progress(
                request.user,
                activity,
            )

        result = {
            "earned_points": earned_points,
            "total_points": total_points,
            "percentage": percentage,
            "passed": passed,
            "passing_score": quiz.passing_score,
        }

    return render(
        request,
        "academy/quiz_take.html",
        {
            "course": course,
            "lesson": lesson,
            "activity": activity,
            "quiz": quiz,
            "questions": questions,
            "attempt": attempt,
            "result": result,
        },
    )

@login_required
def quiz_history(request, course_slug):
    """
    Display all quiz attempts made by the authenticated student
    for a course.
    """

    course = get_object_or_404(
        Course,
        slug=course_slug,
    )

    if not _is_enrolled(
        request.user,
        course,
    ):
        return render(
            request,
            "academy/lesson_locked.html",
            {
                "course": course,
                "lesson": None,
                "previous_lesson": None,
                "enrollment_required": True,
            },
        )

    attempts = list(
        QuizAttempt.objects
        .filter(
            student=request.user,
            quiz__activity__lesson__course=course,
        )
        .select_related(
            "quiz",
            "quiz__activity",
            "quiz__activity__lesson",
        )
        .prefetch_related(
            "quiz__questions",
        )
        .order_by(
            "-created_at",
            "-id",
        )
    )

    history = []

    for attempt in attempts:

        total_points = sum(
            question.points
            for question in attempt.quiz.questions.all()
            if question.is_active
        )

        percentage = (
            round(
                (attempt.score / total_points) * 100,
                1,
            )
            if total_points
            else 0
        )

        history.append(
            {
                "attempt": attempt,
                "quiz": attempt.quiz,
                "activity": attempt.quiz.activity,
                "lesson": attempt.quiz.activity.lesson,
                "score": attempt.score,
                "total_points": total_points,
                "percentage": percentage,
                "passed": attempt.passed,
                "completed_at": (
                    attempt.completed_at
                    or attempt.created_at
                ),
            }
        )

    return render(
        request,
        "academy/quiz_history.html",
        {
            "course": course,
            "history": history,
        },
    )


@login_required
def quiz_attempt_review(request, course_slug, attempt_id):
    """
    Display detailed answers and scoring for one quiz attempt.
    """

    course = get_object_or_404(
        Course,
        slug=course_slug,
    )

    if not _is_enrolled(
        request.user,
        course,
    ):
        return render(
            request,
            "academy/lesson_locked.html",
            {
                "course": course,
                "lesson": None,
                "previous_lesson": None,
                "enrollment_required": True,
            },
        )

    attempt = get_object_or_404(
        QuizAttempt.objects
        .select_related(
            "quiz",
            "quiz__activity",
            "quiz__activity__lesson",
        ),
        id=attempt_id,
        student=request.user,
        quiz__activity__lesson__course=course,
    )

    questions = list(
        attempt.quiz.questions
        .filter(is_active=True)
        .order_by("order", "id")
        .prefetch_related("choices")
    )

    answers = (
        QuizAnswer.objects
        .filter(attempt=attempt)
        .select_related(
            "question",
            "selected_choice",
        )
    )

    answers_by_question = {
        answer.question_id: answer
        for answer in answers
    }

    review = []

    total_points = sum(
        question.points
        for question in questions
    )

    for question in questions:

        answer = answers_by_question.get(
            question.id
        )

        correct_choice = (
            question.choices
            .filter(is_correct=True)
            .order_by("order", "id")
            .first()
        )

        if answer is None:
            selected_choice = None
            is_correct = False
            points_awarded = 0
            status = "Not answered"
        else:
            selected_choice = answer.selected_choice
            is_correct = answer.is_correct
            points_awarded = answer.points_awarded

            status = (
                "Correct"
                if is_correct
                else "Incorrect"
            )

        review.append(
            {
                "question": question,
                "selected_choice": selected_choice,
                "correct_choice": correct_choice,
                "is_correct": is_correct,
                "points_awarded": points_awarded,
                "status": status,
            }
        )

    percentage = (
        round(
            (attempt.score / total_points) * 100,
            1,
        )
        if total_points
        else 0
    )

    return render(
        request,
        "academy/quiz_attempt_review.html",
        {
            "course": course,
            "attempt": attempt,
            "quiz": attempt.quiz,
            "activity": attempt.quiz.activity,
            "lesson": attempt.quiz.activity.lesson,
            "review": review,
            "total_points": total_points,
            "percentage": percentage,
        },
    )


# ============================================================
# COURSE CERTIFICATE
# ============================================================

@login_required
def course_certificate(request, course_slug):
    """
    Display a printable course certificate only after the learner
    has completed every lesson's required activities.
    """

    course = get_object_or_404(
        Course,
        slug=course_slug,
    )

    if not _is_enrolled(
        request.user,
        course,
    ):
        return render(
            request,
            "academy/course_certificate.html",
            {
                "course": course,
                "certificate_available": False,
                "error_message": (
                    "You must be enrolled in this course "
                    "to access its certificate."
                ),
            },
            status=403,
        )

    progress = _course_progress(
        request.user,
        course,
    )

    certificate_available = (
        progress["lessons_total"] > 0
        and progress["lessons_completed"]
        == progress["lessons_total"]
    )

    if not certificate_available:
        return render(
            request,
            "academy/course_certificate.html",
            {
                "course": course,
                "certificate_available": False,
                "progress": progress,
                "error_message": (
                    "Complete all required activities in the course "
                    "before accessing the certificate."
                ),
            },
            status=403,
        )

    learner_name = (
        request.user.get_full_name().strip()
        or request.user.username
    )

    certificate, created = Certificate.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={
            "learner_name": learner_name,
            "course_title": course.title,
            "average_score": progress["average_score"],
        },
    )

    if not created:
        certificate_updates = {}

        if certificate.learner_name != learner_name:
            certificate_updates["learner_name"] = learner_name

        if certificate.course_title != course.title:
            certificate_updates["course_title"] = course.title

        if certificate.average_score != progress["average_score"]:
            certificate_updates["average_score"] = progress["average_score"]

        if certificate_updates:
            Certificate.objects.filter(
                pk=certificate.pk,
            ).update(**certificate_updates)

            certificate.refresh_from_db()

    verification_url = request.build_absolute_uri(
        reverse(
            "certificate_verify",
            args=[certificate.verification_code],
        )
    )

    return render(
        request,
        "academy/course_certificate.html",
        {
            "course": course,
            "certificate_available": True,
            "learner_name": certificate.learner_name,
            "issued_on": timezone.localdate(certificate.issued_at),
            "progress": progress,
            "certificate": certificate,
            "verification_url": verification_url,
        },
    )


# ============================================================
# CERTIFICATE VERIFICATION
# ============================================================

def certificate_verify(request, verification_code):
    """
    Public certificate verification endpoint.
    """

    certificate = get_object_or_404(
        Certificate,
        verification_code=verification_code,
    )

    return render(
        request,
        "academy/certificate_verify.html",
        {
            "certificate": certificate,
            "is_verified": certificate.is_valid,
        },
        status=200,
    )


@login_required
def course_progress(request, course_slug):
    """Display the authenticated student's progress for a course."""

    course = get_object_or_404(Course, slug=course_slug)

    # --------------------------------------------------------
    # ENROLLMENT CHECK
    # --------------------------------------------------------

    if not _is_enrolled(
        request.user,
        course,
    ):
        return render(
            request,
            "academy/lesson_locked.html",
            {
                "course": course,
                "lesson": None,
                "previous_lesson": None,
                "enrollment_required": True,
            },
            status=403,
        )

    progress = _course_progress(request.user, course)

    next_activity = _next_required_activity(
        request.user,
        course,
    )

    modules = list(
        course.modules.prefetch_related("lessons").all()
    )

    for module in modules:
        module_data = _module_progress(request.user, module)
        module.progress = module_data["percentage"]
        module.completed_lessons = module_data["completed_lessons"]
        module.total_lessons = module_data["total_lessons"]
        module.is_completed = module_data["percentage"] == 100

        for lesson in module.lessons.all():
            lesson.is_completed = _lesson_is_completed(
                request.user,
                lesson,
            )

    course_completed = (
        progress["lessons_total"] > 0
        and progress["lessons_completed"] == progress["lessons_total"]
    )

    return render(
        request,
        "academy/course_progress.html",
        {
            "course": course,
            "progress": progress,
            "modules": modules,
            "course_completed": course_completed,
            "next_activity": next_activity,
            "recent_submissions": progress["recent_submissions"],
            "recent_assessments": progress["recent_assessments"],
        },
    )


# ============================================================
# ACCESS / LOCKING HELPERS
# ============================================================

def _is_enrolled(student, course):
    """
    Return True when an authenticated student is enrolled
    in the specified course.
    """
    if not student.is_authenticated:
        return False

    return Enrollment.objects.filter(
        student=student,
        course=course,
    ).exists()


def _is_lesson_completed(student, lesson):
    """
    Return True when all required activities in a lesson
    have been completed by the student.
    """
    return _lesson_is_completed(student, lesson)


def _is_lesson_unlocked(student, lesson):
    """
    Determine whether a student is allowed to access a lesson.

    Rules:
    - First lesson in a course is unlocked.
    - A lesson requires the previous lesson to be completed.
    - If the lesson is the first lesson in a module, the previous
      module must also be completed.
    """
    if not student.is_authenticated:
        return False

    # --------------------------------------------------------
    # Previous lesson in the same module
    # --------------------------------------------------------

    previous_lesson = (
        Lesson.objects
        .filter(
            course=lesson.course,
            module=lesson.module,
            order__lt=lesson.order,
        )
        .order_by("-order")
        .first()
    )

    if previous_lesson:
        return _is_lesson_completed(
            student,
            previous_lesson,
        )

    # --------------------------------------------------------
    # First lesson in a module
    # --------------------------------------------------------

    if lesson.module_id:
        module = lesson.module

        previous_module = (
            Module.objects
            .filter(
                course=lesson.course,
                order__lt=module.order,
            )
            .order_by("-order")
            .first()
        )

        if previous_module:
            previous_module_activities = Activity.objects.filter(
                lesson__module=previous_module,
                is_required=True,
            )

            previous_module_completed = (
                ActivityCompletion.objects.filter(
                    student=student,
                    activity__in=previous_module_activities,
                ).count()
            )

            previous_module_total = previous_module_activities.count()

            if (
                previous_module_total > 0
                and previous_module_completed < previous_module_total
            ):
                return False

    return True


def _is_activity_unlocked(student, activity):
    """
    An activity is accessible only when its lesson is unlocked.
    """
    return _is_lesson_unlocked(
        student,
        activity.lesson,
    )


def _next_required_activity(student, course):
    """
    Return the first incomplete required activity that the student
    is currently allowed to access.

    The existing lesson-unlock and activity-completion rules are
    reused so dashboard and progress pages recommend only accessible
    learning content.
    """
    lessons = (
        Lesson.objects
        .filter(course=course)
        .prefetch_related("activities")
        .order_by("order", "id")
    )

    for lesson in lessons:
        if not _is_lesson_unlocked(
            student,
            lesson,
        ):
            continue

        required_activities = list(
            lesson.activities
            .filter(is_required=True)
            .order_by("order", "id")
        )

        if not required_activities:
            continue

        completed_activity_ids = set(
            ActivityCompletion.objects.filter(
                student=student,
                activity__in=required_activities,
            ).values_list(
                "activity_id",
                flat=True,
            )
        )

        for activity in required_activities:
            if activity.id not in completed_activity_ids:
                return activity

    return None



# ============================================================
# PROGRESS HELPERS
# ============================================================

def _mark_progress(student, activity):
    """Mark an activity as completed for a student."""
    ActivityCompletion.objects.get_or_create(
        student=student,
        activity=activity,
    )


def _lesson_is_completed(student, lesson):
    """
    A lesson is complete when all required activities
    belonging to the lesson have been completed.

    Optional activities do not prevent lesson completion.
    """

    required_activities = lesson.activities.filter(
        is_required=True,
    )

    total_required = required_activities.count()

    if total_required == 0:
        return True

    completed_required = ActivityCompletion.objects.filter(
        student=student,
        activity__in=required_activities,
    ).count()

    return completed_required == total_required



def _course_progress(student, course):
    """
    Calculate lesson, activity, assessment, and score progress
    for a student in a course.
    """

    lessons = Lesson.objects.filter(
        course=course
    ).order_by("order", "id")

    total_lessons = lessons.count()

    completed_lessons = sum(
        1
        for lesson in lessons
        if _lesson_is_completed(student, lesson)
    )

    lesson_percentage = (
        round(
            (completed_lessons / total_lessons) * 100
        )
        if total_lessons
        else 0
    )

    activities = Activity.objects.filter(
        lesson__course=course
    )

    total_activities = activities.count()

    completed_activities = ActivityCompletion.objects.filter(
        student=student,
        activity__lesson__course=course,
    ).count()

    activity_percentage = (
        round(
            (completed_activities / total_activities) * 100
        )
        if total_activities
        else 0
    )

    # --------------------------------------------------------
    # Coding / assignment submissions
    # --------------------------------------------------------

    graded_submissions = list(
        Submission.objects
        .filter(
            student=student,
            activity__lesson__course=course,
            score__isnull=False,
        )
        .select_related(
            "activity",
            "activity__lesson",
        )
        .order_by("-submitted_at", "-id")
    )

    # Keep submission history intact, but count only the best
    # graded submission for each activity in the course average.
    # This mirrors the existing best-attempt rule used for quizzes.
    best_submission_percentages = {}

    for submission in graded_submissions:
        max_score = submission.activity.max_score or 0

        if max_score <= 0:
            continue

        percentage = (
            (submission.score / max_score) * 100
        )

        current_best = best_submission_percentages.get(
            submission.activity_id
        )

        if (
            current_best is None
            or percentage > current_best
        ):
            best_submission_percentages[
                submission.activity_id
            ] = percentage

    submission_percentages = list(
        best_submission_percentages.values()
    )

    # --------------------------------------------------------
    # Quiz attempts
    #
    # Keep only the latest completed attempt for each quiz.
    # --------------------------------------------------------

    quiz_attempts = list(
        QuizAttempt.objects
        .filter(
            student=student,
            quiz__activity__lesson__course=course,
            completed_at__isnull=False,
        )
        .select_related(
            "quiz",
            "quiz__activity",
            "quiz__activity__lesson",
        )
        .prefetch_related(
            "quiz__questions",
        )
        .order_by("-created_at", "-id")
    )

    latest_quiz_attempts = []

    seen_quizzes = set()

    for attempt in quiz_attempts:
        if attempt.quiz_id in seen_quizzes:
            continue

        seen_quizzes.add(attempt.quiz_id)
        latest_quiz_attempts.append(attempt)

    # --------------------------------------------------------
    # Best quiz attempt per quiz for the course average.
    #
    # Quiz history still preserves every attempt, but a later
    # failed retry must not erase a student's earlier result.
    # --------------------------------------------------------

    best_quiz_percentages = {}

    for attempt in quiz_attempts:

        total_points = sum(
            question.points
            for question in attempt.quiz.questions.all()
            if question.is_active
        )

        if not total_points:
            continue

        percentage = (
            (attempt.score / total_points) * 100
        )

        current_best = best_quiz_percentages.get(
            attempt.quiz_id
        )

        if (
            current_best is None
            or percentage > current_best
        ):
            best_quiz_percentages[
                attempt.quiz_id
            ] = percentage

    quiz_percentages = list(
        best_quiz_percentages.values()
    )

    # --------------------------------------------------------
    # Combined average score
    # --------------------------------------------------------

    all_percentages = (
        submission_percentages
        + quiz_percentages
    )

    average_score = (
        round(
            sum(all_percentages) / len(all_percentages),
            1,
        )
        if all_percentages
        else None
    )

    # --------------------------------------------------------
    # Recent submissions
    #
    # Kept for backward compatibility with existing code.
    # --------------------------------------------------------

    recent_submissions = list(
        Submission.objects
        .filter(
            student=student,
            activity__lesson__course=course,
        )
        .select_related(
            "activity",
            "activity__lesson",
        )
        .order_by("-submitted_at", "-id")[:5]
    )

    # --------------------------------------------------------
    # Combined recent assessments
    # --------------------------------------------------------

    recent_assessments = []

    for submission in recent_submissions:

        percentage = None

        if (
            submission.score is not None
            and submission.activity.max_score
        ):
            percentage = round(
                (
                    submission.score
                    / submission.activity.max_score
                ) * 100,
                1,
            )

        if submission.status == "correction":
            status = "Needs correction"
        elif submission.score is not None:
            status = "Graded"
        elif submission.status == "error":
            status = "Error"
        else:
            status = "Pending"

        recent_assessments.append(
            {
                "kind": "submission",
                "title": submission.activity.title,
                "lesson_title": submission.activity.lesson.title,
                "submitted_at": submission.submitted_at,
                "score": submission.score,
                "max_score": submission.activity.max_score,
                "percentage": percentage,
                "status": status,
                "feedback": submission.feedback,
            }
        )

    for attempt in latest_quiz_attempts:

        total_points = sum(
            question.points
            for question in attempt.quiz.questions.all()
            if question.is_active
        )

        percentage = (
            round(
                (attempt.score / total_points) * 100,
                1,
            )
            if total_points
            else 0
        )

        recent_assessments.append(
            {
                "kind": "quiz",
                "title": attempt.quiz.activity.title,
                "lesson_title": attempt.quiz.activity.lesson.title,
                "submitted_at": (
                    attempt.completed_at
                    or attempt.created_at
                ),
                "score": attempt.score,
                "max_score": total_points,
                "percentage": percentage,
                "status": (
                    "Quiz Passed"
                    if attempt.passed
                    else "Not passed"
                ),
                "feedback": None,
            }
        )

    recent_assessments.sort(
        key=lambda item: item["submitted_at"],
        reverse=True,
    )

    recent_assessments = recent_assessments[:5]

    return {
        "lessons_total": total_lessons,
        "lessons_completed": completed_lessons,
        "lesson_percentage": lesson_percentage,
        "activities_total": total_activities,
        "activities_completed": completed_activities,
        "activity_percentage": activity_percentage,
        "average_score": average_score,
        "recent_submissions": recent_submissions,
        "recent_assessments": recent_assessments,

        # Backward-compatible keys
        "total": total_activities,
        "completed": completed_activities,
        "percentage": activity_percentage,
    }


def _module_progress(student, module):
    """Calculate activity and lesson completion for a module."""

    lessons = module.lessons.all()
    total_lessons = lessons.count()

    completed_lessons = sum(
        1
        for lesson in lessons
        if _lesson_is_completed(
        student,
        lesson,
        )
    )

    activities = Activity.objects.filter(
        lesson__module=module,
    )
    total_activities = activities.count()

    completed_activities = ActivityCompletion.objects.filter(
        student=student,
        activity__lesson__module=module,
    ).count()

    percentage = (
        round((completed_activities / total_activities) * 100)
        if total_activities
        else 0
    )

    return {
        "total": total_activities,
        "completed": completed_activities,
        "percentage": percentage,
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
    }
