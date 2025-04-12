import json

from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import List, Movie
from ..serializers import ListDetailSerializer, ListSerializer


class ListViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = ListSerializer

    def get_queryset(self):
        return (
            List.objects.annotate(
                likes_count=Count("likes", distinct=True), movies_count=Count("movies", distinct=True)
            )
            .select_related("creator")
            .prefetch_related("movies", "likes")
        )

    def get_serializer_class(self):
        if self.action in ["retrieve", "create", "update", "partial_update"]:
            return ListDetailSerializer
        return ListSerializer

    def perform_create(self, serializer):
        # Create list
        list_obj = serializer.save(creator=self.request.user)

        # Add movies if provided
        movie_ids = self.request.data.get("movie_ids", "[]")
        if movie_ids:
            movie_ids = json.loads(movie_ids)
            query = Q()
            for movie in movie_ids:
                query |= Q(tmdb_id=movie["tmdb_id"], type=movie["type"])
            movies = Movie.objects.filter(query)
            list_obj.movies.set(movies)

    def perform_update(self, serializer):
        # Update list
        list_obj = serializer.save()

        # Update movies if provided
        movie_ids = self.request.data.get("movie_ids")
        if movie_ids:
            movie_ids = json.loads(movie_ids)
            query = Q()
            for movie in movie_ids:
                print("movie item:", movie)
                query |= Q(tmdb_id=movie["tmdb_id"], type=movie["type"])
            print("query: ", query)
            movies = Movie.objects.filter(query)
            print(movies)
            list_obj.movies.set(movies)

    @action(detail=False, methods=["GET"])
    def featured(self, request):
        """Get trending and staff picks lists"""
        lists = List.objects.get_featured_lists()

        # Split into trending and staff picks
        trending = lists.filter(is_staff_pick=False)[:10]
        staff_picks = lists.filter(is_staff_pick=True)[:10]

        response_data = {
            "trending": self.get_serializer(trending, many=True).data,
            "staff_picks": self.get_serializer(staff_picks, many=True).data,
        }
        return Response(response_data)

    @action(detail=False, methods=["GET"])
    def my_lists(self, request):
        """Get lists created by the authenticated user"""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        lists = List.objects.get_user_lists(request.user)
        serializer = self.get_serializer(lists, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["GET"])
    def liked(self, request):
        """Get lists liked by the authenticated user"""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        lists = List.objects.get_liked_lists(request.user)
        serializer = self.get_serializer(lists, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["GET"])
    def community(self, request):
        """Get popular and recent lists from the community"""
        lists = List.objects.get_community_lists()

        # Split into popular and recent
        popular = lists.order_by("-likes_count")[:10]
        recent = lists.order_by("-created_at")[:10]

        response_data = {
            "popular": self.get_serializer(popular, many=True).data,
            "recent": self.get_serializer(recent, many=True).data,
        }
        return Response(response_data)

    @action(detail=True, methods=["POST"])
    def like(self, request, pk=None):
        """Toggle like status for a list"""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        list_obj = self.get_object()
        user = request.user

        if list_obj.likes.filter(id=user.id).exists():
            list_obj.likes.remove(user)
            liked = False
        else:
            list_obj.likes.add(user)
            liked = True

        return Response({"liked": liked})
