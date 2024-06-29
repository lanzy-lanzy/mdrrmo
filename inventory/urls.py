# myapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    # Define other URL patterns for suppliers, parts, and vehicles
]
