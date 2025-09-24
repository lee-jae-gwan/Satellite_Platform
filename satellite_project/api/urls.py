from django.urls import path
from .views import UploadSatelliteImage
from .views import index_page
from .views import get_presigned_url
from .views import get_presigned_folderurl
from .views import minio_event

urlpatterns = [
    path('upload/', UploadSatelliteImage.as_view(), name= 'upload-satellite'),
    path('',index_page, name = 'index_page'),
    path('get_presigned_url/', get_presigned_url, name='get_presigned_url'),
    path('get_presigned_folderurl/', get_presigned_folderurl, name='get_presigned_folderurl'),
    path('minio_event/',minio_event, name = 'minio_event' ),
]


