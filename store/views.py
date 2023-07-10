from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, F
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from taggit.models import Tag

from .models import Product, Cart, BlackListedToken
from . import serializers
from . import permissions


class ResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 10


class ProductListView(generics.ListAPIView):
    permission_classes = []
    serializer_class = serializers.ProductListSerializer
    pagination_class = ResultsSetPagination

    def get_queryset(self):
        my_query_set = Product.objects.all().order_by('id')
        query = self.request.query_params.get('query')
        tag = self.request.query_params.get('tag')

        if tag is not None and tag !="":
            try:
                tag_id = Tag.objects.get(name=tag)
                my_query_set = my_query_set.filter(tags__in=[tag_id])
            except ObjectDoesNotExist as e:
                my_query_set = Product.objects.none()

        if query is not None and query != "":
            my_query_set = my_query_set.annotate(
                similarity1=TrigramSimilarity('name', query),
                similarity2=TrigramSimilarity('description', query),
            ).filter(Q(similarity1__gt=0.1) | Q(similarity2__gt=0.1))\
                .annotate(similaritysum=F('similarity1')*2 + F('similarity2'))\
                .order_by('-similaritysum', '-similarity1', '-similarity2', '-rate')

        return my_query_set


class AddProductView(generics.CreateAPIView):
    queryset = Product.objects.all()
    permission_classes = [IsAuthenticated, permissions.IsTokenValid, IsAdminUser]
    serializer_class = serializers.ProductSerializer


class RetrieveUpdateDestroyCartView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Cart.objects.all()
    permission_classes = [IsAuthenticated, permissions.IsOwner]
    serializer_class = serializers.CartSerializer
    throttle_classes = [UserRateThrottle]

    def destroy(self, request, *args, **kwargs):
        if 'pk' not in kwargs:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        cart = get_object_or_404(Cart, pk=kwargs['pk'])
        if cart.status != Cart.Status.DRAFT:
            raise ValidationError('can\'t delete not draft cart')
        cart.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListCreateCartView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.CartSerializer
    pagination_class = ResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        return Cart.objects.filter(customer=user)


class ProductView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAdminOrReadOnly]
    serializer_class = serializers.ProductSerializer
    queryset = Product.objects.all()


class RegisterView(generics.CreateAPIView):
    permission_classes = []
    serializer_class = serializers.RegisterSerializer
    queryset = User.objects.all()


class RegisterAdminView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, permissions.IsTokenValid, IsAdminUser]
    serializer_class = serializers.RegisterSerializer
    queryset = User.objects.all()


class ListCartAdminView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, permissions.IsTokenValid, IsAdminUser]
    serializer_class = serializers.CartAdminSerializer
    queryset = Cart.objects.all()
    pagination_class = ResultsSetPagination


class RUDCartAdmin(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, permissions.IsTokenValid, IsAdminUser]
    serializer_class = serializers.CartAdminSerializer
    queryset = Cart.objects.all()


class DeliveryCartView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, permissions.IsTokenValid, permissions.IsDelivery]
    serializer_class = serializers.DeliveryCartSerializer
    queryset = Cart.objects.all()


class RetrieveUserView(APIView):
    permission_classes = [IsAuthenticated, permissions.IsTokenValid]
    serializer_class = serializers.DeliveryCartSerializer
    queryset = User.objects.all()

    def get(self, request, format=None):
        return Response(data=serializers.RetrieveUserSerializer(request.user).data, status=200)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated, permissions.IsTokenValid]

    def post(self, request, format=None):
        user = request.user
        token = request.auth
        BlackListedToken.objects.create(user=user, token=token)
        return Response(data='user logged out!', status=200)
