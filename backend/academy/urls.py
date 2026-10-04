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
    # STUDENT NOTIFICATIONS
    # ========================================================

    path(
        "notifications/",
        views.notification_list,
        name="notification_list",
    ),

    path(
        "notifications/<int:notification_id>/read/",
        views.notification_read,
        name="notification_read",
    ),

    # ========================================================
    # STUDENT ASSESSMENT HISTORY
    # ========================================================

    path(
        "assessments/",
        views.student_assessment_history,
        name="student_assessment_history",
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
    # STUDENT RESUBMISSION
    # ========================================================

    path(
        "assessments/<int:submission_id>/resubmit/",
        views.student_resubmit_submission,
        name="student_resubmit_submission",
    ),

    # ========================================================
    # INSTRUCTOR SUBMISSIONS
    # ========================================================

    path(

        "instructor/quizzes/",

        views.instructor_quizzes,

        name="instructor_quizzes",

    ),


    path(

        "instructor/quizzes/<int:quiz_id>/",

        views.instructor_quiz_edit,

        name="instructor_quiz_edit",

    ),


    path(
        "instructor/assessments/",
        views.instructor_assessment_center,
        name="instructor_assessment_center",
    ),

    path(
        "instructor/students/",
        views.instructor_student_progress_center,
        name="instructor_student_progress_center",
    ),

    path(
        "instructor/students/<int:student_id>/",
        views.instructor_student_progress_detail,
        name="instructor_student_progress_detail",
    ),

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
        "submissions/<int:submission_id>/attachment/",
        views.submission_attachment,
        name="submission_attachment",
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
# QUIZ
# ========================================================

path(
    "<slug:course_slug>/lessons/<int:lesson_id>/activities/<int:activity_id>/quiz/",
    views.quiz_take,
    name="quiz_take",
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
        "<slug:course_slug>/quiz-history/",
        views.quiz_history,
        name="quiz_history",
    ),
    path(
        "<slug:course_slug>/quiz-history/<int:attempt_id>/",
        views.quiz_attempt_review,
        name="quiz_attempt_review",
    ),
    
    # ========================================================
    path(
        "certificates/verify/<uuid:verification_code>/",
        views.certificate_verify,
        name="certificate_verify",
    ),

    # COURSE CERTIFICATE
    # ========================================================

    path(
        "<slug:course_slug>/certificate/",
        views.course_certificate,
        name="course_certificate",
    ),

    path(
        "<slug:course_slug>/progress/",
        views.course_progress,
        name="course_progress",
    ),

    # ========================================================
    # COURSE DETAIL
    # ========================================================

    # ========================================================
    # INSTRUCTOR COURSE CONTENT
    # ========================================================

    path(
        "instructor/content/",
        views.instructor_content_management,
        name="instructor_content_management",
    ),

    path(
        "instructor/content/<int:course_id>/",
        views.instructor_course_content,
        name="instructor_course_content",
    ),

    # ========================================================
    # INSTRUCTOR DASHBOARD
    # ========================================================

    path(
        "instructor/",
        views.instructor_dashboard,
        name="instructor_dashboard",
    ),

    path(
        "<slug:slug>/",
        views.course_detail,
        name="course_detail",
    ),
]


