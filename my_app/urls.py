from django.urls import path, include
from .views import FileOperationsViewSet
from rest_framework.routers import DefaultRouter

from my_app import views

router = DefaultRouter()
router.register(r'file-operations', FileOperationsViewSet, basename= 'file-operations')

urlpatterns = [
    path('', include(router.urls))
]