import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from .fixtures import auth_api_superuser, create_superuser, auth_api_user, create_user


@pytest.mark.django_db
def test_register():
    url = reverse('register')
    response = APIClient().post(url, data={'username': 'user', 'email': 'user@example.com', 'password': '12345678!', 'password2': '12345678!'})
    assert response.status_code == status.HTTP_201_CREATED

    url = reverse('token-obtain-pair')
    api_client = APIClient()
    response = api_client.post(url, {'username': 'user', 'password': '12345678!'})
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_register_admin(auth_api_superuser):
    url = reverse('register')
    response = auth_api_superuser.post(url, data={'username': 'user', 'email': 'user@example.com', 'password': '12345678!', 'password2': '12345678!', 'type': 'admin'})
    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.get(username='user').is_superuser


@pytest.mark.django_db
def test_register_invalid_email():
    url = reverse('register')
    response = APIClient().post(url, data={'username': 'user', 'email': 'user', 'password': '12345678!', 'password2': '12345678!'})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert str({'email': ['Enter a valid email address.']}) in str(response.json())


@pytest.mark.django_db
def test_login(create_user):
    api_client = APIClient()
    response = api_client.post(reverse('token-obtain-pair'), {'username': create_user.username, 'password': '123'})
    assert response.status_code == status.HTTP_200_OK
    assert 'access' in str(response.json())


@pytest.mark.django_db
def test_register_login_logout():
    url = reverse('register')
    response = APIClient().post(url, data={'username': 'user', 'email': 'user@example.com', 'password': '12345678!',
                                           'password2': '12345678!'})
    assert response.status_code == status.HTTP_201_CREATED

    url = reverse('token-obtain-pair')
    api_client = APIClient()
    response = api_client.post(url, {'username': 'user', 'password': '12345678!'})
    assert response.status_code == status.HTTP_200_OK
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.json()['access'])
    response = api_client.get(reverse('retrieve-user'))
    assert response.status_code == status.HTTP_200_OK

    response = api_client.post(reverse('logout'), {})
    assert response.status_code == status.HTTP_200_OK

    response = api_client.get(reverse('retrieve-user'))
    assert response.status_code == status.HTTP_403_FORBIDDEN



