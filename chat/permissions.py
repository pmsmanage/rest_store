from rest_framework import permissions
from .models import Chat


class IsChatMember(permissions.BasePermission):
    def has_permission(self, request, view):
        chat_id = view.kwargs.get('pk', None)
        user = request.user
        return user.chats.contains(Chat(pk=chat_id))
