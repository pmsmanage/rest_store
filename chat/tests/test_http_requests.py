import json

import pytest
from django.urls import reverse
from rest_framework import status
from .fixtures import auth_api_user, create_user, create_superuser
from ..models import Chat


@pytest.mark.django_db
def test_chat_list(auth_api_user, create_user, create_superuser):
    url = reverse('chat-list')
    response = auth_api_user.get(url)
    assert response.status_code == status.HTTP_200_OK
    chat = Chat.objects.create()
    chat.users.add(create_user)
    chat.users.add(create_superuser)
    chat.save()
    response = auth_api_user.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert "'users': ['user', 'admin']" in str(response.json())
