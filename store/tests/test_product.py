import re

from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
import pytest
from taggit.models import Tag
from .fixtures import create_superuser, auth_api_superuser, products, auth_api_user, create_user


@pytest.mark.django_db
def test_index_page():
    url = reverse('index')
    response = APIClient().get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_add_product(auth_api_superuser):
    url = reverse('add-product')
    response = auth_api_superuser.post(url, data={'name': 'p1', 'rate': 0})
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_add_product_not_admin(auth_api_user):
    url = reverse('add-product')
    response = auth_api_user.post(url, data={'name': 'p1', 'rate': 0})
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_show_product(products):
    url = reverse('RUD-product', kwargs={'pk': products[0].id})
    response = APIClient().get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_update_product(products, auth_api_superuser):
    url = reverse('RUD-product', kwargs={'pk': products[0].id})
    response = auth_api_superuser.put(url, data={'name': 'p8'})
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_update_product_not_admin(products, auth_api_user):
    url = reverse('RUD-product', kwargs={'pk': products[0].id})
    response = auth_api_user.put(url, data={'name': 'p8'})
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_delete_product(auth_api_superuser, products):
    url = reverse('RUD-product', kwargs={'pk': products[0].id})
    response = auth_api_superuser.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_search_products_with_tag(products):
    tag1 = Tag.objects.create(name='tag1')
    tag2 = Tag.objects.create(name='tag2')

    products[0].tags.add(tag1)
    products[0].save()
    products[1].tags.add(tag1)
    products[1].save()
    products[2].tags.add(tag2)
    products[2].save()

    url = reverse('index')
    api_client = APIClient()
    response = api_client.get(url, {'tag': tag1.name})
    assert response.status_code == status.HTTP_200_OK
    response_body = str(response.json())
    assert str(products[0].get_absolute_url()) in response_body
    assert str(products[1].get_absolute_url()) in response_body
    assert str(products[2].get_absolute_url()) not in response_body


@pytest.mark.django_db
def test_search_products_with_query(products):
    products[0].name = 'wood'
    products[0].save()
    products[1].name = 'wool'
    products[1].save()
    products[2].name = 'blanket'
    products[2].save()

    url = reverse('index')
    api_client = APIClient()
    response = api_client.get(url, {'query': 'wool'})
    assert response.status_code == status.HTTP_200_OK
    assert re.search(f".*{products[1].get_absolute_url()}.*{products[0].get_absolute_url()}.*", str(response.json()))
    assert str(products[2].get_absolute_url()) not in str(response.json())
