from django.urls import path

from . import views


urlpatterns = [
    path("", views.course_list, name="course_list"),

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

    path(
        "<slug:course_slug>/lessons/<int:lesson_id>/activities/<int:activity_id>/submissions/",
        views.submission_history,
        name="submission_history",
    ),

    path(
        "<slug:course_slug>/lessons/<int:lesson_id>/activities/<int:activity_id>/",
        views.activity_detail,
        name="activity_detail",
    ),

    path(
        "<slug:course_slug>/lessons/<int:lesson_id>/",
        views.lesson_detail,
        name="lesson_detail",
    ),

    path(
        "<slug:course_slug>/progress/",
        views.course_progress,
        name="course_progress",
    ),

    path(
        "<slug:slug>/",
        views.course_detail,
        name="course_detail",
    ),
]
