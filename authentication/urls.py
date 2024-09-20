from django.urls import path
from rest_framework.authtoken import views

from authentication.views import SignUpView

urlpatterns = [
    path('login', views.obtain_auth_token, name="login"),
    path('sign-up', SignUpView.as_view(), name="sign_up")
]
