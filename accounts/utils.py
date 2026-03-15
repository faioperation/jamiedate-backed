import random
from django.utils import timezone
from datetime import timedelta
from accounts.models import PasswordResetOTP
from django.template.loader import render_to_string
from django.core.mail import EmailMessage


def generate_otp():
    return str(random.randint(100000, 999999))


def can_resend_otp(user):
    last_otp = (
        PasswordResetOTP.objects.filter(user=user).order_by("-created_at").first()
    )
    if not last_otp:
        return True
    return timezone.now() > last_otp.created_at + timedelta(seconds=30)


def create_otp(user):
    # Delete old unverified OTPs
    PasswordResetOTP.objects.filter(user=user, verified=False).delete()

    return PasswordResetOTP.objects.create(user=user, code=generate_otp())


def verify_otp(user, otp_code):
    otp_obj = PasswordResetOTP.objects.filter(user=user, verified=False).first()

    if not otp_obj:
        return False, "OTP expired or invalid"

    if otp_obj.is_expired():
        otp_obj.delete()
        return False, "OTP expired"

    if otp_obj.code != otp_code:
        return False, "Invalid OTP"

    otp_obj.verified = True
    otp_obj.save()
    return True, "OTP verified"


def send_otp_email(email, otp):
    subject = "Verify Your Password"
    html_content = render_to_string("emails/verify_email.html", {"OTP": otp})

    email_msg = EmailMessage(
        subject=subject,
        body=html_content,
        to=[email],
    )
    email_msg.content_subtype = "html"
    email_msg.send()
