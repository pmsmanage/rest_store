from django.urls import path
from . import views

urlpatterns = [
    path('', views.ChatListView.as_view(), name="chat-list"),
    path('<int:pk>/', views.ChatView.as_view(), name='view-chat'),
]
