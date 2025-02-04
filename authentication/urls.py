from django.urls import path
from rest_framework.authtoken import views

from authentication.views import SignUpView, UserProfileUpdateView

urlpatterns = [
    path('login', views.obtain_auth_token, name="login"),
    path('register', SignUpView.as_view(), name="register"),
    path('me', UserProfileUpdateView.as_view(), name="me"),
]
