from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import Movie, Favorite
from ..serializers import MovieSerializer


class FavoriteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorites = Favorite.objects.filter(user=request.user).select_related('movie')
        movies = [favorite.movie for favorite in favorites]
        serializer = MovieSerializer(movies, many=True)
        return Response(serializer.data)

    def post(self, request):
        tmdb_id = request.data.get('tmdb_id')
        if not tmdb_id:
            return Response({'error': 'tmdb_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            movie = Movie.objects.get(tmdb_id=tmdb_id)
        except Movie.DoesNotExist:
            return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)

        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            movie=movie
        )

        if not created:
            return Response({'error': 'Movie already in favorites'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_201_CREATED)

    def delete(self, request, tmdb_id):
        try:
            movie = Movie.objects.get(tmdb_id=tmdb_id)
            favorite = Favorite.objects.get(user=request.user, movie=movie)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Movie.DoesNotExist:
            return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
        except Favorite.DoesNotExist:
            return Response({'error': 'Movie not in favorites'}, status=status.HTTP_404_NOT_FOUND)
