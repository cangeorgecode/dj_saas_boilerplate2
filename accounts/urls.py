from django.urls import path, include
from . import views
from core import views as core_views

urlpatterns = [
    path('', include('allauth.urls')),
    path('profile/', views.profile, name='profile'),
    path('check-username/', views.check_username, name='check_username'),
]