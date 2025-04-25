from django.contrib.auth import authenticate
from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, generics, status
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Favorite, Watchlist

from .models import User
from .serializers import (
    SignUpSerializer,
    UserMinimalSerializer,
    UserProfileSerializer,
    UserSettingsSerializer,
    WatchlistItemSerializer,
)


class StandardResultsPagination(PageNumberPagination):
    """Standard pagination for API results"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "count": self.page.paginator.count,
                "results": data,
            }
        )


class UserFollowersListView(generics.ListAPIView):
    """
    Retrieve a user's followers list with pagination and search functionality.

    Returns a paginated list of users who follow the specified user.
    If the user's profile is private, only the user themselves can see their followers.
    """

    serializer_class = UserMinimalSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "full_name"]

    @swagger_auto_schema(
        operation_description="Get a user's followers list with pagination",
        manual_parameters=[
            openapi.Parameter(
                "search", openapi.IN_QUERY, description="Search by username or full name", type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description="Successfully retrieved followers list",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "next": openapi.Schema(
                            type=openapi.TYPE_STRING, nullable=True, description="URL for next page"
                        ),
                        "previous": openapi.Schema(
                            type=openapi.TYPE_STRING, nullable=True, description="URL for previous page"
                        ),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER, description="Total count of items"),
                        "results": openapi.Schema(
                            type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                    },
                ),
            ),
            403: "Forbidden - Private profile",
            404: "Not Found - User not found",
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        username = self.kwargs.get("username")
        try:
            user = User.objects.get(username=username)

            # Check if the profile is private and the requester is not the owner
            if not user.is_public and (self.request.user.is_anonymous or user != self.request.user):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("This profile is private")

            # Get followers with search functionality if provided
            queryset = user.followers.all()
            search_query = self.request.query_params.get("search", None)
            if search_query:
                queryset = queryset.filter(Q(username__icontains=search_query) | Q(full_name__icontains=search_query))

            return queryset
        except User.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("User not found")


class UserFollowingListView(generics.ListAPIView):
    """
    Retrieve a user's following list with pagination and search functionality.

    Returns a paginated list of users who follow the specified user.
    If the user's profile is private, only the user themselves can see their followers.
    """

    serializer_class = UserMinimalSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "full_name"]

    @swagger_auto_schema(
        operation_description="Get a user's following list with pagination",
        manual_parameters=[
            openapi.Parameter(
                "search", openapi.IN_QUERY, description="Search by username or full name", type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description="Successfully retrieved following list",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "next": openapi.Schema(
                            type=openapi.TYPE_STRING, nullable=True, description="URL for next page"
                        ),
                        "previous": openapi.Schema(
                            type=openapi.TYPE_STRING, nullable=True, description="URL for previous page"
                        ),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER, description="Total count of items"),
                        "results": openapi.Schema(
                            type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                    },
                ),
            ),
            403: "Forbidden - Private profile",
            404: "Not Found - User not found",
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        username = self.kwargs.get("username")
        try:
            user = User.objects.get(username=username)

            # Check if the profile is private and the requester is not the owner
            if not user.is_public and (self.request.user.is_anonymous or user != self.request.user):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("This profile is private")

            # Get followers with search functionality if provided
            queryset = user.following.all()
            search_query = self.request.query_params.get("search", None)
            if search_query:
                queryset = queryset.filter(Q(username__icontains=search_query) | Q(full_name__icontains=search_query))

            return queryset
        except User.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("User not found")


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="Login with username/email and password",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["login", "password"],
            properties={
                "login": openapi.Schema(type=openapi.TYPE_STRING, description="Username or email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password", description="Password"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Successfully logged in",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "token": openapi.Schema(type=openapi.TYPE_STRING, description="Authentication token"),
                    },
                ),
            ),
            401: "Unauthorized - Invalid credentials",
        },
    )
    def post(self, request):
        login = request.data.get("login")
        password = request.data.get("password")

        if not login or not password:
            return Response({"error": "Please provide both login and password"}, status=status.HTTP_400_BAD_REQUEST)

        # Try to authenticate with username
        user = authenticate(username=login, password=password)

        # If username authentication fails, try email
        if not user:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            try:
                username = User.objects.get(email=login).username
                user = authenticate(username=username, password=password)
            except User.DoesNotExist:
                pass

        if not user:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})


class SignUpView(APIView):
    """
    User registration endpoint.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="Register a new user account",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "email", "password", "full_name"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="Unique username"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", description="Valid email address"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password", description="Strong password"),
                "full_name": openapi.Schema(type=openapi.TYPE_STRING, description="User's full name"),
            },
        ),
        responses={
            201: openapi.Response(
                description="Successfully registered",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "token": openapi.Schema(type=openapi.TYPE_STRING, description="Authentication token"),
                    },
                ),
            ),
            400: "Bad Request - Invalid data provided",
        },
    )
    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileUpdateView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update user profile information.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get current user's profile information",
        responses={
            200: UserProfileSerializer,
            401: "Unauthorized - Invalid or missing token",
            403: "Forbidden - Not authenticated",
        },
        security=[{"Token": []}],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update current user's profile information",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "full_name": openapi.Schema(type=openapi.TYPE_STRING, description="User's full name"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", description="Email address"),
                "about": openapi.Schema(type=openapi.TYPE_STRING, description="User bio/about information"),
                "profile_image": openapi.Schema(type=openapi.TYPE_FILE, description="Profile picture"),
                "banner_image": openapi.Schema(type=openapi.TYPE_FILE, description="Profile banner image"),
            },
        ),
        responses={
            200: UserProfileSerializer,
            400: "Bad Request - Invalid data",
            401: "Unauthorized - Invalid or missing token",
            403: "Forbidden - Not authenticated",
        },
        security=[{"Token": []}],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        return self.request.user


class UserPublicView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    lookup_field = "username"

    def get_object(self):
        obj = super().get_object()
        # Check if the user's profile is public or if the requester is the owner
        if not obj.is_public and (self.request.user.is_anonymous or obj != self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("This profile is private")
        return obj


class UserFollowUnfollowView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    lookup_field = "username"

    def create(self, request, *args, **kwargs):
        user = self.request.user
        user_to_follow = self.get_object()
        print(user, user_to_follow)
        if user_to_follow == user:
            return Response({"error": "You cannot follow yourself"}, status=status.HTTP_400_BAD_REQUEST)

        if user_to_follow in user.following.all():
            user.following.remove(user_to_follow)
            return Response({"message": "Unfollowed successfully", "status": "unfollowed"}, status=status.HTTP_200_OK)
        user.following.add(user_to_follow)
        return Response({"message": "Followed successfully", "status": "followed"}, status=status.HTTP_200_OK)


class UserSettingsView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update user settings.
    """

    serializer_class = UserSettingsSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get current user's settings",
        responses={
            200: UserSettingsSerializer,
            401: "Unauthorized - Invalid or missing token",
            403: "Forbidden - Not authenticated",
        },
        security=[{"Token": []}],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update current user's settings",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "is_public": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN, description="Whether the profile is publicly visible"
                ),
            },
        ),
        responses={
            200: UserSettingsSerializer,
            400: "Bad Request - Invalid data",
            401: "Unauthorized - Invalid or missing token",
            403: "Forbidden - Not authenticated",
        },
        security=[{"Token": []}],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        return self.request.user


class UserWatchlistView(generics.ListAPIView):
    """
    Retrieve the current user's watchlist items with filtering options.

    Allows filtering by:
    - status: Filter by watchlist status (watchlist, watched, watching)
    - is_favorite: Filter by whether the movie is in user's favorites
    - search: Search in movie titles
    """

    serializer_class = WatchlistItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    @swagger_auto_schema(
        operation_description="Get current user's watchlist items with filtering",
        manual_parameters=[
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter by status (watchlist, watched, watching)",
                type=openapi.TYPE_STRING,
                enum=["watchlist", "watched", "watching"],
            ),
            openapi.Parameter(
                "is_favorite",
                openapi.IN_QUERY,
                description="Filter by favorite status (true, false)",
                type=openapi.TYPE_BOOLEAN,
            ),
            openapi.Parameter(
                "search",
                openapi.IN_QUERY,
                description="Search for movies by title",
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Successfully retrieved watchlist items",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "next": openapi.Schema(
                            type=openapi.TYPE_STRING, nullable=True, description="URL for next page"
                        ),
                        "previous": openapi.Schema(
                            type=openapi.TYPE_STRING, nullable=True, description="URL for previous page"
                        ),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER, description="Total count of items"),
                        "results": openapi.Schema(
                            type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                    },
                ),
            ),
            401: "Unauthorized - Invalid or missing token",
        },
        security=[{"Token": []}],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = Watchlist.objects.filter(user=user).select_related("movie")

        # Filter by status if provided
        status = self.request.query_params.get("status", None)
        if status and status in [choice[0] for choice in Watchlist.Statuses.choices]:
            queryset = queryset.filter(status=status)

        # Filter by favorite status if provided
        is_favorite = self.request.query_params.get("is_favorite", None)
        if is_favorite is not None:
            is_favorite = is_favorite.lower() == "true"
            # Get list of favorite movie IDs for this user
            favorite_movie_ids = Favorite.objects.filter(user=user).values_list("movie_id", flat=True)

            if is_favorite:
                queryset = queryset.filter(movie_id__in=favorite_movie_ids)
            else:
                queryset = queryset.exclude(movie_id__in=favorite_movie_ids)
        
        # Search by movie title if provided
        search_query = self.request.query_params.get("search", None)
        if search_query:
            queryset = queryset.filter(movie__title__icontains=search_query)

        return queryset.order_by("-updated_at")
