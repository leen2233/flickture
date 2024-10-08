from rest_framework.authtoken.models import Token
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import SignUpSerializer, UserProfileSerializer


class SignUpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # Save the user
            # Create a token for the newly created user
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
