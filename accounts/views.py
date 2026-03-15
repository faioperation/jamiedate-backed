from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts import serializers as sz
from accounts.models import User
from api.permissions import IsAdminRole
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class SelfProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Get logged-in user profile",
        responses={200: sz.SelfProfileSerializer()},
        tags=["Auth / Account"],
    )
    def get(self, request):
        serializer = sz.SelfProfileSerializer(request.user)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update logged-in user profile",
        request_body=sz.SelfProfileSerializer,
        responses={200: sz.SelfProfileSerializer()},
        tags=["Auth / Account"],
    )
    def patch(self, request):
        serializer = sz.SelfProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    @swagger_auto_schema(
        operation_summary="List all users",
        responses={200: sz.UserManagementSerializer(many=True)},
        tags=["Admin / Users"],
    )
    def get(self, request):
        users = User.objects.all().order_by("-id")
        serializer = sz.UserManagementSerializer(users, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create new user",
        request_body=sz.UserManagementSerializer,
        responses={201: "User created"},
        tags=["Admin / Users"],
    )
    def post(self, request):
        serializer = sz.UserManagementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "User created successfully"},
            status=status.HTTP_201_CREATED,
        )


class UserDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    @swagger_auto_schema(
        operation_summary="Delete a user",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_PATH,
                description="ID of the user to delete",
                type=openapi.TYPE_INTEGER,
            )
        ],
        responses={200: "User deleted"},
        tags=["Admin / Users"],
    )
    def delete(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        # superuser check
        if user.is_superuser:
            return Response(
                {"error": "Superuser cannot be deleted"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.delete()

        return Response(
            {"message": "User deleted successfully"},
            status=status.HTTP_200_OK,
        )


class LoginView(APIView):
    @swagger_auto_schema(
        operation_summary="User Login",
        operation_description="Login user using email & password. Returns JWT tokens.",
        request_body=sz.LoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                examples={
                    "application/json": {
                        "message": "Login successful",
                        "tokens": {"refresh": "string", "access": "string"},
                    }
                },
            ),
            400: "Invalid email or password",
        },
        tags=["Auth / Account"],
    )
    def post(self, request):
        serializer = sz.LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        return Response(
            {
                "message": "Login successful",
                "tokens": {
                    "refresh": serializer.validated_data["refresh"],
                    "access": serializer.validated_data["access"],
                },
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                    "name": f"{user.name}",
                    "profile_image": (
                        request.build_absolute_uri(user.profile_image.url)
                        if user.profile_image
                        else None
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Change password",
        request_body=sz.ChangePasswordSerializer,
        responses={200: openapi.Response("Password changed successfully")},
        tags=["Auth / Account"],
    )
    def post(self, request):
        serializer = sz.ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Password changed successfully"},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Forgot Password | Send password reset OTP",
        request_body=sz.ForgotPasswordSerializer,
        responses={200: openapi.Response(description="OTP sent")},
        tags=["Auth / Password Reset"],
    )
    def post(self, request):
        serializer = sz.ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "OTP sent to email"}, status=status.HTTP_200_OK)


class VerifyOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify Otp",
        request_body=sz.VerifyOtpSerializer,
        responses={200: openapi.Response(description="OTP verified")},
        tags=["Auth / Password Reset"],
    )
    def post(self, request):
        serializer = sz.VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"message": "OTP verified"}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Reset Password",
        request_body=sz.ResetPasswordSerializer,
        responses={200: openapi.Response(description="Reset Password successfully")},
        tags=["Auth / Password Reset"],
    )
    def post(self, request):
        serializer = sz.ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password reset successfully"}, status=status.HTTP_200_OK
        )


class ResendOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Resend OTP",
        request_body=sz.ResendOtpSerializer,
        responses={200: openapi.Response(description="OTP sent")},
        tags=["Auth / Password Reset"],
    )
    def post(self, request):
        serializer = sz.ResendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "OTP sent to email"}, status=status.HTTP_200_OK)


class CustomTokenRefreshView(TokenRefreshView):

    @swagger_auto_schema(
        operation_summary="Refresh Access Token",
        request_body=sz.TokenRefreshSerializer,
        responses={
            200: openapi.Response(
                description="New access token",
                examples={"application/json": {"access": "string"}},
            )
        },
        tags=["Auth / Account"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
