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

    @action(detail=True, methods=["POST"])
    def add_movie(self, request, pk=None):
        """Add a movie to a list"""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        list_obj = self.get_object()

        # Check if user is the creator of the list
        if list_obj.creator != request.user:
            return Response({"detail": "You can only modify your own lists"}, status=status.HTTP_403_FORBIDDEN)

        # Get movie data from request
        try:
            tmdb_id = request.data.get("tmdb_id")
            movie_type = request.data.get("type")

            if not tmdb_id or not movie_type:
                return Response(
                    {"detail": "Movie data must include tmdb_id and type"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Find the movie
            try:
                movie = Movie.objects.get(tmdb_id=tmdb_id, type=movie_type)
            except Movie.DoesNotExist:
                return Response({"detail": "Movie not found"}, status=status.HTTP_404_NOT_FOUND)

            # Check if movie is already in the list
            if list_obj.movies.filter(tmdb_id=tmdb_id, type=movie_type).exists():
                return Response({"detail": "Movie already in list"}, status=status.HTTP_400_BAD_REQUEST)

            # Add movie to list
            list_obj.movies.add(movie)

            return Response({"detail": "Movie added to list"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["POST"])
    def remove_movie(self, request, pk=None):
        """Remove a movie from a list"""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        list_obj = self.get_object()

        # Check if user is the creator of the list
        if list_obj.creator != request.user:
            return Response({"detail": "You can only modify your own lists"}, status=status.HTTP_403_FORBIDDEN)

        # Get movie data from request
        try:
            tmdb_id = request.data.get("tmdb_id")
            movie_type = request.data.get("type")

            if not tmdb_id or not movie_type:
                return Response(
                    {"detail": "Movie data must include tmdb_id and type"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Find the movie in the list
            try:
                movie = list_obj.movies.get(tmdb_id=tmdb_id, type=movie_type)
            except Movie.DoesNotExist:
                return Response({"detail": "Movie not in list"}, status=status.HTTP_404_NOT_FOUND)

            # Remove movie from list
            list_obj.movies.remove(movie)

            return Response({"detail": "Movie removed from list"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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

    @action(detail=True, methods=["GET"])
    def check_movie(self, request, pk=None):
        """Check if a movie is in a list"""
        list_obj = self.get_object()

        # Get movie ID from query parameters
        tmdb_id = request.query_params.get("tmdb_id")
        movie_type = request.query_params.get("type")

        if not tmdb_id or not movie_type:
            return Response(
                {"detail": "Movie tmdb_id and type are required query parameters"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if movie exists in the list
        exists = list_obj.movies.filter(tmdb_id=tmdb_id, type=movie_type).exists()

        return Response({"exists": exists})
