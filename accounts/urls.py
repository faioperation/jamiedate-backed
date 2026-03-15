from django.urls import path

from accounts.views import (
    SelfProfileView,
    LoginView,
    ChangePasswordView,
    ForgotPasswordView,
    VerifyOtpView,
    ResetPasswordView,
    ResendOtpView,
    CustomTokenRefreshView,
    UserListCreateView,
    UserDeleteView,
)


urlpatterns = [
    path("users/", UserListCreateView.as_view()),
    path("users/<int:user_id>/", UserDeleteView.as_view()),
    path("me/", SelfProfileView.as_view(), name="self-profile"),
    path("login/", LoginView.as_view(), name="login"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("verify-otp/", VerifyOtpView.as_view(), name="verify-otp"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("resend-otp/", ResendOtpView.as_view(), name="resend-otp"),
    path("token/refresh/", CustomTokenRefreshView.as_view()),
]
