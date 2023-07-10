from rest_framework import permissions
from django.contrib.auth.models import Group
from .models import BlackListedToken


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.id == obj.customer.id


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_superuser and IsTokenValid.has_permission(self, request, view)


class IsDelivery(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='delivery').exists()


class IsTokenValid(permissions.BasePermission):
    def has_permission(self, request, view):
        user_id = request.user.id
        is_allowed_user = True
        token = request.auth
        try:
            is_blacklisted = BlackListedToken.objects.get(user=user_id, token=token)
            if is_blacklisted:
                is_allowed_user = False
        except BlackListedToken.DoesNotExist:
            is_allowed_user = True
        return is_allowed_user
