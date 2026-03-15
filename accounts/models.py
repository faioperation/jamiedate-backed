from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from accounts.managers import CustomUserManager


# Create your models here.
class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    TESTER = "TESTER", "Tester"


class User(AbstractUser):

    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    business_name = models.TextField(blank=True, null=True)
    website = models.TextField(blank=True, null=True)
    role = models.CharField(
        max_length=20, choices=UserRole.choices, default=UserRole.ADMIN
    )
    profile_image = models.ImageField(upload_to="users/profile/", null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.name} "


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)
