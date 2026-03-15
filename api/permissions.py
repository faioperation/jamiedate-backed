from rest_framework.permissions import BasePermission
from accounts.models import UserRole


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.ADMIN
