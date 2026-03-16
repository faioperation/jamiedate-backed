from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import User, PasswordResetOTP
from accounts.utils import (
    can_resend_otp,
    create_otp,
    verify_otp,
    send_otp_email,
)


from rest_framework import serializers


class UserManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "role",
            "profile_image",
            "password",
        ]
        read_only_fields = ["id"]

        extra_kwargs = {
            "password": {"write_only": True},
            "profile_image": {"required": False},
        }

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class SelfProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "business_name",
            "website",
            "profile_image",
            "role",
        ]
        read_only_fields = ["id", "email", "role"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            request=self.context.get("request"),
            email=data["email"],
            password=data["password"],
        )

        if not user:
            raise serializers.ValidationError("Invalid email or password")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")

        refresh = RefreshToken.for_user(user)

        return {
            "user": user,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match"}
            )
        return data

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.strip().lower()
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User not found")
        return value

    def save(self):
        user = User.objects.get(email=self.validated_data["email"])

        if not can_resend_otp(user):
            raise serializers.ValidationError(
                "Please wait 30 seconds before resending OTP"
            )

        otp_obj = create_otp(user)
        send_otp_email(user.email, otp_obj.code)


class VerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        email = data["email"].strip().lower()
        otp_code = data["otp"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        is_valid, message = verify_otp(user, otp_code)
        if not is_valid:
            raise serializers.ValidationError(message)

        return data


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")

        email = data["email"].strip().lower()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        # Check if OTP verified
        if not PasswordResetOTP.objects.filter(user=user, verified=True).exists():
            raise serializers.ValidationError("OTP not verified")

        return data

    def save(self):
        email = self.validated_data["email"].strip().lower()
        new_password = self.validated_data["new_password"]
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()

        # Delete OTP after successful reset
        PasswordResetOTP.objects.filter(user=user).delete()
        return user


class ResendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.strip().lower()
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User not found")
        return value

    def save(self):
        user = User.objects.get(email=self.validated_data["email"])

        if not can_resend_otp(user):
            raise serializers.ValidationError(
                "Please wait 30 seconds before resending OTP"
            )

        otp_obj = create_otp(user)
        send_otp_email(user.email, otp_obj.code)


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()
