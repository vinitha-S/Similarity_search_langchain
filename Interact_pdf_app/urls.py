# urls.py
from django.urls import path
from .views import UploadedFileCreateAPIView
urlpatterns = [
    path('', UploadedFileCreateAPIView.as_view(), name='upload_file'),
]
