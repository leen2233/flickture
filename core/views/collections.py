from rest_framework import generics
from rest_framework.permissions import AllowAny

from core.models import Collection
from core.serializers import CollectionSerializer


class CollectionDetailAPIView(generics.RetrieveAPIView):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    lookup_field = "tmdb_id"
    permission_classes = [AllowAny]
