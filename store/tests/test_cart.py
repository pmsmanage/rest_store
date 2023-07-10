import pytest
from django.urls import reverse
from django.core import mail
from rest_framework import status
from .fixtures import auth_api_user, create_user, products, create_superuser, auth_api_superuser
from ..models import Cart
from django.contrib.auth.models import Group
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_cart_list(auth_api_user):
    url = reverse('list-create-cart')
    response = auth_api_user.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_create_cart(auth_api_user, products):
    url = reverse('list-create-cart')
    response = auth_api_user.post(url, data={'products': products[0].id})
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_create_cart_multiple_products(auth_api_user, products):
    url = reverse('list-create-cart')
    response = auth_api_user.post(url, data={'products': (products[0].id,
                                                          products[1].id,
                                                          products[0].id)})

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_create_invalid_cart(auth_api_user):
    url = reverse('list-create-cart')
    response = auth_api_user.post(url, data={})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert str({'products': 'at least 1 product must be add'}) in str(response.json())


@pytest.mark.django_db
def test_update_cart(auth_api_user, products, django_user_model):
    cart = Cart()
    cart.customer = django_user_model.objects.get(username='user')
    cart.save()
    cart.products.add(products[0])
    cart.products.add(products[1])
    cart.save()
    url = reverse('RUD-cart', kwargs={'pk': cart.id})
    response = auth_api_user.put(url, data={'products': (products[0].id, products[0].id)})
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_update_cart_from_another_user(auth_api_user, products, django_user_model, create_superuser):
    cart = Cart()
    cart.customer = django_user_model.objects.get(username=create_superuser.username)
    cart.save()
    cart.products.add(products[0])
    cart.products.add(products[1])
    cart.save()
    url = reverse('RUD-cart', kwargs={'pk': cart.id})
    response = auth_api_user.put(url, data={'products': (products[0].id, products[0].id)})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert str({'detail': 'You do not have permission to perform this action.'}) in str(response.json())


@pytest.mark.django_db
def test_update_order_cart(auth_api_user, products, django_user_model, auth_api_superuser):
    cart = Cart()
    cart.customer = django_user_model.objects.get(username='user')
    cart.save()
    cart.products.add(products[0])
    cart.save()
    url = reverse('RUD-cart', kwargs={'pk': cart.id})
    # normal flow
    response = auth_api_user.put(url, data={'products': (products[0].id,)})
    assert response.status_code == status.HTTP_200_OK

    # another user trying to update the cart
    response = auth_api_superuser.put(url, data={'products': (products[0].id,)})
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # trying to set status to on the way (shouldn't be allowed)
    response = auth_api_user.put(url, data={'status': Cart.Status.ON_WAY})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # setting status to ordered
    response = auth_api_user.put(url, data={'products': (products[0].id,), 'status': Cart.Status.ORDERED})
    assert response.status_code == status.HTTP_200_OK
    assert f"'status': '{Cart.Status.ORDERED}'" in str(response.json())
    assert "'order_date': None" not in str(response.json())

    # trying to update after status was changed to ordered
    response = auth_api_user.put(url, data={'products': (products[0].id,)})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # trying to change status back to draft
    response = auth_api_user.put(url, data={'status': Cart.Status.DRAFT})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_delete_cart(auth_api_user, products, django_user_model):
    cart = Cart()
    cart.customer = django_user_model.objects.get(username='user')
    cart.save()
    cart.products.add(products[0])
    cart.save()
    url = reverse('RUD-cart', kwargs={'pk': cart.id})

    response = auth_api_user.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = auth_api_user.delete(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_create_cart_admin(auth_api_superuser, products, create_user):
    url = reverse('list-create-cart-admin')
    response = auth_api_superuser.post(url, data={'customer': create_user.id, 'products': products[0].id})
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_create_cart_admin_not_admin(auth_api_user, products, create_user):
    url = reverse('list-create-cart-admin')
    response = auth_api_user.post(url, data={'customer': create_user.id, 'products': products[0].id})
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_update_cart_admin(auth_api_superuser, products, create_user, auth_api_user):
    url = reverse('list-create-cart-admin')
    response = auth_api_superuser.post(url, data={'customer': create_user.id, 'products': products[0].id})
    assert response.status_code == status.HTTP_201_CREATED

    url = reverse('RUD-cart-admin', kwargs={'pk': Cart.objects.all()[0].id})
    response = auth_api_superuser.put(url, data={'customer': create_user.id, 'products': products[0].id})
    assert response.status_code == status.HTTP_200_OK

    response = auth_api_user.put(url, data={'customer': create_user.id, 'products': products[0].id})
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_delete_cart_admin(auth_api_superuser, products, create_user, auth_api_user):
    cart = Cart()
    cart.customer = create_user
    cart.status = Cart.Status.ORDERED
    cart.save()
    cart.products.set(products)
    cart.save()

    url = reverse('RUD-cart-admin', kwargs={'pk': cart.id})
    response = auth_api_user.delete(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = auth_api_superuser.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_retrieve_cart_admin(auth_api_superuser, products, create_user, auth_api_user):
    cart = Cart()
    cart.customer = create_user
    cart.status = Cart.Status.ORDERED
    cart.save()
    cart.products.set(products)
    cart.save()

    url = reverse('RUD-cart-admin', kwargs={'pk': cart.id})
    response = auth_api_user.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = auth_api_superuser.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert str(url) in str(response.json())


@pytest.mark.django_db
@pytest.mark.parametrize('cart_status', [
   (Cart.Status.ON_WAY,),
   (Cart.Status.REJECTED,)
])
def test_receive_email_on_way(cart_status, products, create_user, auth_api_superuser):
    cart = Cart()
    cart.customer = create_user
    cart.status = Cart.Status.ORDERED
    cart.save()
    cart.products.set(products)
    cart.save()
    url = reverse('RUD-cart-admin', kwargs={'pk': cart.id})
    response = auth_api_superuser.put(url, data={'status': cart_status})
    assert response.status_code == status.HTTP_200_OK
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_delivery_update_cart(create_user, create_superuser, products):
    group = Group.objects.create(name='delivery')
    user = create_user
    user.groups.add(group)
    user.save()
    from rest_framework.test import APIClient
    api_client = APIClient()
    response = api_client.post(reverse('token-obtain-pair'), {'username': user.username, 'password': '123'})
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.json()['access'])
    cart = Cart()
    cart.customer = create_superuser
    cart.status = Cart.Status.ON_WAY
    cart.save()
    cart.products.set(products)
    cart.save()
    url = reverse('delivery-cart', kwargs={'pk': cart.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    response = api_client.put(url)
    assert response.status_code == status.HTTP_200_OK
    cart = Cart.objects.get(pk=cart.id)
    assert cart.status == Cart.Status.DELIVERED


