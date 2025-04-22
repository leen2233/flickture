from django.urls import path

from authentication.views import (
    LoginView,
    SignUpView,
    UserFollowUnfollowView,
    UserProfileUpdateView,
    UserPublicView,
    UserSettingsView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", SignUpView.as_view(), name="register"),
    path("me/", UserProfileUpdateView.as_view(), name="me"),
    path("settings/", UserSettingsView.as_view(), name="settings"),
    path("user/<str:username>/", UserPublicView.as_view(), name="user_public"),
    path("user/<str:username>/follow/", UserFollowUnfollowView.as_view(), name="user_follow"),
]
