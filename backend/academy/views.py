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
    courses = Course.objects.all()

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
    Display a course together with its modules and lessons.
    """
    course = get_object_or_404(
        Course.objects.prefetch_related(
            "modules__lessons",
            "lessons__activities",
        ),
        slug=slug,
    )

    modules = course.modules.all()

    # Lessons that do not yet belong to a module
    unassigned_lessons = course.lessons.filter(
        module__isnull=True
    ).prefetch_related("activities")

    context = {
        "course": course,
        "modules": modules,
        "unassigned_lessons": unassigned_lessons,
    }

    # Add progress information for authenticated students
    if request.user.is_authenticated:
        context["course_progress"] = _course_progress(
            request.user,
            course
        )

        context["module_progress"] = {
            module.id: _module_progress(
                request.user,
                module
            )
            for module in modules
        }

    return render(
        request,
        "academy/course_detail.html",
        context,
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
    Display an activity and handle coding submissions.

    IMPORTANT:
    Python code execution is allowed only when DEBUG=True.

    This prevents arbitrary submitted Python code from being
    executed directly on a public production server.
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

    # --------------------------------------------------------
    # Handle POST
    # --------------------------------------------------------

    if request.method == "POST":

        # User must be authenticated to submit work
        if not request.user.is_authenticated:
            return redirect(
                f"/accounts/login/?next={request.path}"
            )

        code = request.POST.get("code", "").strip()

        # ----------------------------------------------------
        # Reading activity
        # ----------------------------------------------------

        if activity.activity_type == "reading":

            _mark_progress(
                request.user,
                activity,
            )

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

            # ------------------------------------------------
            # Production protection
            # ------------------------------------------------

            elif not settings.DEBUG:

                error = (
                    "The online code runner is currently unavailable "
                    "in production. Code execution is disabled for "
                    "security reasons."
                )

            else:
                # --------------------------------------------
                # Local development code execution
                # --------------------------------------------

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
                        f"An error occurred while running your code: "
                        f"{exc}"
                    )

                # --------------------------------------------
                # Save submission
                # --------------------------------------------

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

                # --------------------------------------------
                # Mark completed only if execution succeeded
                # --------------------------------------------

                if not error:
                    _mark_progress(
                        request.user,
                        activity,
                    )

        # ----------------------------------------------------
        # Other activity types
        # ----------------------------------------------------

        else:

            _mark_progress(
                request.user,
                activity,
            )

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

    if not request.user.is_staff:
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

    if not request.user.is_staff:
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
            "reviewed"
        ).strip()

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
def course_progress(
    request,
    course_slug,
):
    """
    Display progress for the authenticated student.
    """

    course = get_object_or_404(
        Course,
        slug=course_slug,
    )

    progress = _course_progress(
        request.user,
        course,
    )

    modules = course.modules.all()

    module_progress = []

    for module in modules:

        module_progress.append(
            {
                "module": module,
                "progress": _module_progress(
                    request.user,
                    module,
                ),
            }
        )

    return render(
        request,
        "academy/course_progress.html",
        {
            "course": course,
            "progress": progress,
            "module_progress": module_progress,
        },
    )


# ============================================================
# PROGRESS HELPERS
# ============================================================

def _mark_progress(
    student,
    activity,
):
    """
    Mark an activity as completed for a student.
    """

    ActivityCompletion.objects.get_or_create(
        student=student,
        activity=activity,
    )


def _course_progress(
    student,
    course,
):
    """
    Calculate overall course activity completion.
    """

    activities = Activity.objects.filter(
        lesson__course=course,
    )

    total = activities.count()

    if total == 0:
        return {
            "total": 0,
            "completed": 0,
            "percentage": 0,
        }

    completed = ActivityCompletion.objects.filter(
        student=student,
        activity__lesson__course=course,
    ).count()

    percentage = round(
        (completed / total) * 100
    )

    return {
        "total": total,
        "completed": completed,
        "percentage": percentage,
    }


def _module_progress(
    student,
    module,
):
    """
    Calculate module activity completion.
    """

    activities = Activity.objects.filter(
        lesson__module=module,
    )

    total = activities.count()

    if total == 0:
        return {
            "total": 0,
            "completed": 0,
            "percentage": 0,
        }

    completed = ActivityCompletion.objects.filter(
        student=student,
        activity__lesson__module=module,
    ).count()

    percentage = round(
        (completed / total) * 100
    )

    return {
        "total": total,
        "completed": completed,
        "percentage": percentage,
    }