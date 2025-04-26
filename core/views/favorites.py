from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Favorite, Movie
from ..serializers import MovieSerializer


class FavoriteAPIView(APIView):
    """API view for managing user's favorite movies."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all movies in user's favorites",
        responses={200: MovieSerializer(many=True), 403: "Forbidden - Not authenticated"},
        security=[{"Token": []}],
    )
    def get(self, request):
        favorites = Favorite.objects.filter(user=request.user).select_related("movie")
        movies = [favorite.movie for favorite in favorites]
        serializer = MovieSerializer(movies, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Add a movie to user's favorites",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["tmdb_id"],
            properties={
                "tmdb_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="TMDB ID of the movie to add to favorites"
                )
            },
        ),
        responses={
            201: "Successfully added to favorites",
            400: "Bad Request - Invalid data or movie already in favorites",
            403: "Forbidden - Not authenticated",
            404: "Movie not found",
        },
        security=[{"Token": []}],
    )
    def post(self, request):
        tmdb_id = request.data.get("tmdb_id")
        type = request.data.get("type")
        if not tmdb_id or not type:
            return Response({"error": "tmdb_id and type are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            movie = Movie.objects.get(tmdb_id=tmdb_id, type=type)
        except Movie.DoesNotExist:
            return Response({"error": "Movie not found"}, status=status.HTTP_404_NOT_FOUND)

        favorite, created = Favorite.objects.get_or_create(user=request.user, movie=movie)

        if not created:
            return Response({"error": "Movie already in favorites"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="Remove a movie from user's favorites",
        responses={
            204: "Successfully removed from favorites",
            403: "Forbidden - Not authenticated",
            404: "Movie not found or not in favorites",
        },
        security=[{"Token": []}],
    )
    def delete(self, request, type, tmdb_id):
        try:
            movie = Movie.objects.get(tmdb_id=tmdb_id, type=type)
            favorite = Favorite.objects.get(user=request.user, movie=movie)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Movie.DoesNotExist:
            return Response({"error": "Movie not found"}, status=status.HTTP_404_NOT_FOUND)
        except Favorite.DoesNotExist:
            return Response({"error": "Movie not in favorites"}, status=status.HTTP_404_NOT_FOUND)
