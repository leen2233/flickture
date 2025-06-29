from django.urls import path

from authentication.views import (
    CaptchaView,
    LoginView,
    SignUpView,
    UserFollowersListView,
    UserFollowingListView,
    UserFollowUnfollowView,
    UserProfileUpdateView,
    UserPublicView,
    UserSettingsView,
    UserWatchlistView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", SignUpView.as_view(), name="register"),
    path("captcha/", CaptchaView.as_view(), name="captcha"),
    path("me/", UserProfileUpdateView.as_view(), name="me"),
    path("settings/", UserSettingsView.as_view(), name="settings"),
    path("user/<str:username>/", UserPublicView.as_view(), name="user_public"),
    path("user/<str:username>/follow/", UserFollowUnfollowView.as_view(), name="user_follow"),
    path("user/<str:username>/followers/", UserFollowersListView.as_view(), name="user_followers"),
    path("user/<str:username>/following/", UserFollowingListView.as_view(), name="user_following"),
    path("user/<str:username>/watchlist/", UserWatchlistView.as_view(), name="watchlist"),
]
