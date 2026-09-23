from django.urls import path

from . import views


urlpatterns = [
    # ========================================================
    # COURSE LIST
    # ========================================================

    path(
        "",
        views.course_list,
        name="course_list",
    ),

    # ========================================================
    # MY COURSES
    # ========================================================

    path(
        "my-courses/",
        views.my_courses,
        name="my_courses",
    ),

    # ========================================================
    # ENROLL IN COURSE
    # ========================================================

    path(
        "<slug:slug>/enroll/",
        views.enroll_course,
        name="enroll_course",
    ),

    # ========================================================
    # INSTRUCTOR SUBMISSIONS
    # ========================================================

    path(
        "instructor/submissions/",
        views.instructor_submissions,
        name="instructor_submissions",
    ),

    path(
        "instructor/submissions/<int:submission_id>/",
        views.review_submission,
        name="review_submission",
    ),

    # ========================================================
    # SUBMISSION HISTORY
    # ========================================================

    path(
        "<slug:course_slug>/lessons/<int:lesson_id>/activities/<int:activity_id>/submissions/",
        views.submission_history,
        name="submission_history",
    ),

    # ========================================================
    # ACTIVITY DETAIL
    # ========================================================

    path(
        "<slug:course_slug>/lessons/<int:lesson_id>/activities/<int:activity_id>/",
        views.activity_detail,
        name="activity_detail",
    ),

    # ========================================================
    # LESSON DETAIL
    # ========================================================

    path(
        "<slug:course_slug>/lessons/<int:lesson_id>/",
        views.lesson_detail,
        name="lesson_detail",
    ),

    # ========================================================
    # COURSE PROGRESS
    # ========================================================

    path(
        "<slug:course_slug>/progress/",
        views.course_progress,
        name="course_progress",
    ),

    # ========================================================
    # COURSE DETAIL
    # ========================================================

    path(
        "<slug:slug>/",
        views.course_detail,
        name="course_detail",
    ),
]