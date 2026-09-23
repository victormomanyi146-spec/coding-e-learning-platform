from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

import os
import subprocess
import tempfile

from .models import (
    Activity,
    ActivityCompletion,
    Course,
    Enrollment,
    Lesson,
    Module,
    Submission,
)


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
# COURSE DETAIL
# ============================================================

def course_detail(request, slug):
    """
    Display a course with its modules, lessons,
    enrollment status, and progress information.
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
        course.modules.all()
    )

    # --------------------------------------------------------
    # GET UNASSIGNED LESSONS
    # --------------------------------------------------------

    unassigned_lessons = course.lessons.filter(
        module__isnull=True
    )

    # --------------------------------------------------------
    # DEFAULT PROGRESS VALUES
    # --------------------------------------------------------

    course_progress_value = {
        "total": 0,
        "completed": 0,
        "percentage": 0,
    }

    module_progress_data = {}

    # --------------------------------------------------------
    # PROGRESS FOR AUTHENTICATED USERS
    # --------------------------------------------------------

    if request.user.is_authenticated:

        # Overall course progress
        course_progress_value = _course_progress(
            request.user,
            course,
        )

        # Calculate progress for every module
        for module in modules:

            progress = _module_progress(
                request.user,
                module,
            )

            module_progress_data[module.id] = progress

            # Attach progress information directly
            # to the module object for the template
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

            # First module is always open
            if module.order == 1:
                continue

            # Find the previous module
            previous_module = next(
                (
                    previous
                    for previous in modules
                    if previous.order == module.order - 1
                ),
                None,
            )

            # Lock this module until previous module is complete
            if previous_module:

                if not getattr(
                    previous_module,
                    "is_completed",
                    False,
                ):
                    module.is_locked = True

        # ----------------------------------------------------
        # LESSON COMPLETION STATUS
        # ----------------------------------------------------

        for module in modules:

            for lesson in module.lessons.all():

                lesson.is_completed = ActivityCompletion.objects.filter(
                    student=request.user,
                    activity__lesson=lesson,
                ).exists()

        # Completion status for lessons without modules
        for lesson in unassigned_lessons:

            lesson.is_completed = ActivityCompletion.objects.filter(
                student=request.user,
                activity__lesson=lesson,
            ).exists()

    else:

        # ----------------------------------------------------
        # DEFAULT VALUES FOR VISITORS
        # ----------------------------------------------------

        for module in modules:

            module.progress = 0
            module.completed_lessons = 0
            module.total_lessons = module.lessons.count()
            module.is_completed = False
            module.is_locked = False

            for lesson in module.lessons.all():
                lesson.is_completed = False

        for lesson in unassigned_lessons:
            lesson.is_completed = False

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
    }

    return render(
        request,
        "academy/course_detail.html",
        context,
    )


# ============================================================
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
    Display courses the authenticated student is enrolled in.
    """

    enrollments = (
        Enrollment.objects
        .filter(student=request.user)
        .select_related("course")
        .order_by("-enrolled_at")
    )

    return render(
        request,
        "academy/my_courses.html",
        {
            "enrollments": enrollments,
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

    # Enforce module sequencing when a lesson belongs to a module.
    if request.user.is_authenticated and lesson.module_id:
        module = lesson.module
        if module.order > 1:
            previous_module = (
                Module.objects
                .filter(course=course, order=module.order - 1)
                .first()
            )

            if previous_module:
                previous_activity_ids = Activity.objects.filter(
                    lesson__module=previous_module,
                ).values_list("id", flat=True)

                previous_total = len(previous_activity_ids)
                previous_completed = ActivityCompletion.objects.filter(
                    student=request.user,
                    activity_id__in=previous_activity_ids,
                ).count()

                if previous_total and previous_completed < previous_total:
                    previous_lesson = (
                        Lesson.objects
                        .filter(module=previous_module)
                        .order_by("-order")
                        .first()
                    )

                    if previous_lesson:
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

    submission = None
    output = None
    error = None
    code = ""
    program_input = ""

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

        if activity.activity_type == "coding":

            if not code:
                error = "Please enter Python code before submitting."

            elif len(code) > 10000:
                error = "Code is too long. Please keep submissions under 10,000 characters."

            elif len(program_input) > 5000:
                error = "Program input is too long. Please keep it under 5,000 characters."

            elif not settings.DEBUG:

                error = (
                    "The online code runner is currently unavailable "
                    "in production. Code execution is disabled for "
                    "security reasons."
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
        # Other activity types
        # ----------------------------------------------------

        else:

            if submit_activity:

                _mark_progress(request.user, activity)
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

    context = {
        "course": course,
        "lesson": lesson,
        "activity": activity,
        "submission": submission,
        "output": output,
        "error": error,
        "code": code,
        "program_input": program_input,
        "is_completed": is_completed,
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
# INSTRUCTOR SUBMISSIONS
# ============================================================

@login_required
def instructor_submissions(request):
    """
    Display submissions for instructor/admin review.

    Staff users can see all submissions.
    """

    if not (request.user.is_staff or request.user.role == "INSTRUCTOR"):
        return HttpResponse(
            "You do not have permission to access this page.",
            status=403,
        )

    submissions = (
        Submission.objects
        .select_related(
            "student",
            "activity",
            "activity__lesson",
            "activity__lesson__course",
        )
        .order_by("-submitted_at")
    )

    return render(
        request,
        "academy/instructor_submissions.html",
        {
            "submissions": submissions,
        },
    )


# ============================================================
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
        # Mark activity complete when graded
        # --------------------------------------------

        if (
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

@login_required
def course_progress(request, course_slug):
    """Display the authenticated student's progress for a course."""

    course = get_object_or_404(Course, slug=course_slug)

    progress = _course_progress(request.user, course)

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
            "recent_submissions": progress["recent_submissions"],
        },
    )


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
    A lesson is considered complete when at least one activity
    belonging to it has been completed.

    This preserves the progress model already used by the project.
    """
    return ActivityCompletion.objects.filter(
        student=student,
        activity__lesson=lesson,
    ).exists()


def _course_progress(student, course):
    """Calculate lesson, activity, and assessment progress."""

    lessons = Lesson.objects.filter(course=course)
    activities = Activity.objects.filter(lesson__course=course)

    total_lessons = lessons.count()

    completed_lesson_ids = set(
        ActivityCompletion.objects.filter(
            student=student,
            activity__lesson__course=course,
        )
        .values_list("activity__lesson_id", flat=True)
        .distinct()
    )

    completed_lessons = len(completed_lesson_ids)

    lesson_percentage = (
        round((completed_lessons / total_lessons) * 100)
        if total_lessons
        else 0
    )

    total_activities = activities.count()

    completed_activities = ActivityCompletion.objects.filter(
        student=student,
        activity__lesson__course=course,
    ).count()

    activity_percentage = (
        round((completed_activities / total_activities) * 100)
        if total_activities
        else 0
    )

    graded_submissions = (
        Submission.objects
        .filter(
            student=student,
            activity__lesson__course=course,
            score__isnull=False,
        )
        .select_related("activity")
    )

    score_percentages = [
        (submission.score / submission.activity.max_score) * 100
        for submission in graded_submissions
        if submission.activity.max_score
    ]

    average_score = (
        round(sum(score_percentages) / len(score_percentages), 1)
        if score_percentages
        else None
    )

    recent_submissions = list(
        Submission.objects
        .filter(
            student=student,
            activity__lesson__course=course,
        )
        .select_related("activity", "activity__lesson")
        .order_by("-submitted_at")[:5]
    )

    return {
        "lessons_total": total_lessons,
        "lessons_completed": completed_lessons,
        "lesson_percentage": lesson_percentage,
        "activities_total": total_activities,
        "activities_completed": completed_activities,
        "activity_percentage": activity_percentage,
        "average_score": average_score,
        "recent_submissions": recent_submissions,

        # Backward-compatible keys
        "total": total_activities,
        "completed": completed_activities,
        "percentage": activity_percentage,
    }


def _module_progress(student, module):
    """Calculate activity and lesson completion for a module."""

    lessons = module.lessons.all()
    total_lessons = lessons.count()

    completed_lesson_ids = set(
        ActivityCompletion.objects.filter(
            student=student,
            activity__lesson__module=module,
        )
        .values_list("activity__lesson_id", flat=True)
        .distinct()
    )

    completed_lessons = len(completed_lesson_ids)

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
