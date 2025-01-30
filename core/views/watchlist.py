from rest_framework import status as status_codes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Movie, Watchlist
from core.serializers import WatchlistSerializer


class WatchlistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        watchlist = Watchlist.objects.filter(user=request.user)
        serializer = WatchlistSerializer(watchlist, many=True)
        return Response(serializer.data)

    def post(self, request):
        tmdb_id = request.data.get('tmdb_id')
        status = request.data.get('status', Watchlist.Statuses.WATCHLIST)

        if not tmdb_id:
            return Response(
                {'error': 'tmdb_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        movie = Movie.objects.get(tmdb_id=tmdb_id)

        watchlist_item, created = Watchlist.objects.get_or_create(
            user=request.user,
            movie=movie,
            defaults={'status': status}
        )

        if not created:
            watchlist_item.status = status
            watchlist_item.save()

        serializer = WatchlistSerializer(watchlist_item)
        return Response(
            serializer.data,
            status=status_codes.HTTP_201_CREATED if created else status_codes.HTTP_200_OK
        )

    def delete(self, request, tmdb_id):
        try:
            watchlist_item = Watchlist.objects.get(
                user=request.user,
                movie__tmdb_id=tmdb_id
            )
            watchlist_item.delete()
            return Response(status=status_codes.HTTP_204_NO_CONTENT)
        except Watchlist.DoesNotExist:
            return Response(
                {'error': 'Movie not found in watchlist'},
                status=status_codes.HTTP_404_NOT_FOUND
            )
