from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from core.models import Watchlist, Movie
from core.serializers import WatchlistSerializer


class WatchlistAPIView(generics.ListCreateAPIView, generics.UpdateAPIView):
    """
    API view for managing user's watchlist.
    Supports listing all watchlist items and adding/updating movies in watchlist.
    """
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all movies in user's watchlist",
        responses={
            200: WatchlistSerializer(many=True),
            403: 'Forbidden - Not authenticated'
        },
        security=[{'Token': []}]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Add a movie to user's watchlist",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['status'],
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['watchlist', 'watching', 'watched'],
                    description='Watchlist status for the movie'
                ),
                'rating': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    minimum=1,
                    maximum=10,
                    description='Optional rating (1-10)'
                ),
                'notes': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Optional notes about the movie'
                )
            }
        ),
        responses={
            201: WatchlistSerializer,
            400: 'Bad Request - Invalid data or movie already in watchlist',
            403: 'Forbidden - Not authenticated',
            404: 'Movie not found'
        },
        security=[{'Token': []}]
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a movie's status in watchlist",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['watchlist', 'watching', 'watched'],
                    description='New watchlist status'
                ),
                'rating': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    minimum=1,
                    maximum=10,
                    description='Optional rating (1-10)'
                ),
                'notes': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Optional notes about the movie'
                )
            }
        ),
        responses={
            200: WatchlistSerializer,
            400: 'Bad Request - Invalid data',
            403: 'Forbidden - Not authenticated',
            404: 'Movie not found in watchlist'
        },
        security=[{'Token': []}]
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user)

    def get_object(self):
        try:
            tmdb_id = self.kwargs.get('tmdb_id')
            movie = Movie.objects.get(tmdb_id=tmdb_id)
            return Watchlist.objects.get(user=self.request.user, movie=movie)
        except Movie.DoesNotExist:
            raise ValidationError({'detail': 'Movie not found'})
        except Watchlist.DoesNotExist:
            raise ValidationError({'detail': 'Movie not in watchlist'})

    def create(self, request, *args, **kwargs):
        try:
            tmdb_id = kwargs.get('tmdb_id')
            if not tmdb_id:
                return Response(
                    {'detail': 'TMDB ID is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            movie = Movie.objects.get(tmdb_id=tmdb_id)

            # Check if movie is already in watchlist
            if Watchlist.objects.filter(user=request.user, movie=movie).exists():
                return Response(
                    {'detail': 'Movie already in watchlist'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Add tmdb_id to request data for serializer
            data = request.data.copy()
            data['tmdb_id'] = str(tmdb_id)

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user, movie=movie)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Movie.DoesNotExist:
            return Response(
                {'detail': 'Movie not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
