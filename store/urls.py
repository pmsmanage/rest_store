from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProductListView.as_view(), name="index"),
    path('add-product/', views.AddProductView.as_view(), name='add-product'),
    path('carts/<int:pk>/', views.RetrieveUpdateDestroyCartView.as_view(), name='RUD-cart'),
    path('carts/', views.ListCreateCartView.as_view(), name='list-create-cart'),
    path('products/<int:pk>/', views.ProductView.as_view(), name='RUD-product'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('carts/admin/', views.ListCartAdminView.as_view(), name='list-create-cart-admin'),
    path('carts/admin/<int:pk>/', views.RUDCartAdmin.as_view(), name='RUD-cart-admin'),
    path('delivery/carts/<int:pk>/', views.DeliveryCartView.as_view(), name='delivery-cart'),
    path('user/', views.RetrieveUserView.as_view(), name='retrieve-user'),
    path('logout/', views.LogoutView.as_view(), name='logout')
]
