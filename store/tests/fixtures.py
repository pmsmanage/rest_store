import pytest
from django.urls import reverse
from ..models import Product
from rest_framework.test import APIClient


@pytest.fixture
def create_user(db, django_user_model):
    user = django_user_model.objects.create_user(username='user', password='123', email='user')
    return user


@pytest.fixture
def create_superuser(db, django_user_model):
    user = django_user_model.objects.create_superuser(username='admin', password='123', email='admin')
    return user


@pytest.fixture
def auth_api_user(db, create_user):
    user = create_user
    api_client = APIClient()
    response = api_client.post(reverse('token-obtain-pair'), {'username': user.username, 'password': '123'})
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.json()['access'])
    return api_client


@pytest.fixture
def auth_api_superuser(db, create_superuser):
    user = create_superuser
    api_client = APIClient()
    response = api_client.post(reverse('token-obtain-pair'), {'username': user.username, 'password': '123'})
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.json()['access'])
    return api_client


@pytest.fixture
def products(db):
    product_list = [Product.objects.create(name='p1'), Product.objects.create(name='p2'), Product.objects.create(name='p3')]
    return product_list

