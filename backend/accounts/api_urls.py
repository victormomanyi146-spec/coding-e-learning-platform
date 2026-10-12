from django.urls import path

from .admin_learning_views import AdminLearningResourceAPIView, AdminLearningResourceDetailAPIView

from .views import (
    AdminLoginAPIView,
    InstructorLoginAPIView,
    StudentRegistrationAPIView,
    StudentLoginAPIView,
    InstructorApplicationCreateAPIView,
    InstructorApplicationVerifyOTPAPIView,
    InstructorApplicationResendOTPAPIView,
    AdminInstructorApplicationListAPIView,
    AdminInstructorApplicationReviewAPIView,
    AdminInstructorApplicationDocumentAPIView,
    AdminAccountListAPIView,
    AdminAccountDetailAPIView,
    AdminOverviewAPIView,
    AdminAuditLogListAPIView,
)


urlpatterns = [
    path("register/", StudentRegistrationAPIView.as_view(), name="student-register"),
    path("instructor-applications/", InstructorApplicationCreateAPIView.as_view(), name="instructor-application-create"),
    path("instructor-applications/verify-otp/", InstructorApplicationVerifyOTPAPIView.as_view(), name="instructor-application-verify-otp"),
    path("instructor-applications/resend-otp/", InstructorApplicationResendOTPAPIView.as_view(), name="instructor-application-resend-otp"),
    path("admin/instructor-applications/", AdminInstructorApplicationListAPIView.as_view(), name="admin-instructor-application-list"),
    path("admin/users/", AdminAccountListAPIView.as_view(), name="admin-account-list"),
    path("admin/users/<int:user_id>/", AdminAccountDetailAPIView.as_view(), name="admin-account-detail"),
    path("admin/overview/", AdminOverviewAPIView.as_view(), name="admin-overview"),
    path("admin/audit-log/", AdminAuditLogListAPIView.as_view(), name="admin-audit-log"),
    path("admin/learning/<slug:resource>/", AdminLearningResourceAPIView.as_view(), name="admin-learning-resource"),
    path("admin/learning/<slug:resource>/<int:item_id>/", AdminLearningResourceDetailAPIView.as_view(), name="admin-learning-resource-detail"),
    path("admin/instructor-applications/<int:application_id>/review/", AdminInstructorApplicationReviewAPIView.as_view(), name="admin-instructor-application-review"),
    path("admin/instructor-applications/<int:application_id>/documents/<str:document_type>/", AdminInstructorApplicationDocumentAPIView.as_view(), name="admin-instructor-application-document"),
    path(
        "login/",
        StudentLoginAPIView.as_view(),
        name="student-login",
    ),
    path(
        "instructor-login/",
        InstructorLoginAPIView.as_view(),
        name="instructor-login",
    ),
    path(
        "admin-login/",
        AdminLoginAPIView.as_view(),
        name="admin-login",
    ),
]
