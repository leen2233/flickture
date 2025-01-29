from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated

from core.models import Watchlist
from core.serializers import WatchlistSerializer


class WatchlistAPIView(generics.ListCreateAPIView):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Watchlist.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
