from django.urls import path
from . import views

urlpatterns = [
    path('images/<str:name>', views.ImageView.as_view(), name='get_image'),
    # path('files/str:name>', views.FileView.as_view(), name='get_files')
]
