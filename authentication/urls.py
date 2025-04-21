from django.urls import path
from rest_framework.authtoken import views

from authentication.views import LoginView, SignUpView, UserProfileUpdateView, UserPublicView

urlpatterns = [
    path('login/', LoginView.as_view(), name="login"),
    path('register/', SignUpView.as_view(), name="register"),
    path('me/', UserProfileUpdateView.as_view(), name="me"),
    path('user/<str:username>/', UserPublicView.as_view(), name="user_public"),
]
