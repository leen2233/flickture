from django.contrib.auth import authenticate
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import SignUpSerializer, UserProfileSerializer


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
    lookup_field = 'username'
