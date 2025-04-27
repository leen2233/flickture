import logging
import pprint

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.models import Collection, Comment, Episode, Movie, MovieCast, Person, Watchlist
from core.serializers import (
    CommentSerializer,
    EpisodeSerializer,
    MovieDetailSerializer,
    MovieListSerializer,
    MovieSerializer,
)
from core.utils.tmdb import TMDBClient

# Initialize TMDB client
tmdb_client = TMDBClient(api_key=settings.TMDB_API_KEY)

# Configure logger
logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class for consistent pagination across views"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class MovieDetailView(generics.RetrieveAPIView):
    """Retrieve detailed movie information."""

    queryset = Movie.objects.all()
    serializer_class = MovieDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        tmdb_id = self.kwargs["tmdb_id"]
        type = self.kwargs["type"]
        try:
            logger.debug(f"MovieDetailView: Fetching movie with TMDB ID: {tmdb_id}")
            movie = Movie.objects.get(tmdb_id=tmdb_id, type=type)
            return movie
        except Movie.DoesNotExist:
            logger.info(f"MovieDetailView: Movie not found locally with TMDB ID: {tmdb_id}, fetching from TMDB")
            try:
                movie_info = None
                if type == "movie":
                    movie_info = tmdb_client.get_movie_details(tmdb_id)
                elif type == "tv":
                    movie_info = tmdb_client.get_tv_details(tmdb_id)

                movie = Movie.objects.create_or_update_from_tmdb(movie_info)
                return movie
            except Exception as e:
                logger.error(f"MovieDetailView: Failed to fetch movie from TMDB: {str(e)}", exc_info=True)
                raise NotFound("Movie not found on TMDB")

    @swagger_auto_schema(
        operation_description="Get detailed information about a specific movie",
        responses={200: MovieDetailSerializer, 404: "Movie not found"},
    )
    # @method_decorator(cache_page(60 * 60 * 24))  # Cache for 24 hours
    def get(self, request, *args, **kwargs):
        try:
            movie = self.get_object()
            logger.debug(f"MovieDetailView: Retrieved movie: {movie.title}")

            if self._should_fetch_details(movie):
                logger.info(f"MovieDetailView: Fetching additional details for movie: {movie.title}")
                movie = self._fetch_movie_details(movie)

            if not movie.cast.exists() or movie.cast.count() < 10:
                logger.info(f"MovieDetailView: Fetching credits for movie: {movie.title}")
                self._fetch_movie_credits(movie)

            serializer = self.get_serializer(movie)
            return Response(serializer.data)

        except NotFound as e:
            logger.warning(f"MovieDetailView: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"MovieDetailView: Unexpected error: {str(e)}", exc_info=True)
            return Response({"detail": "Failed to fetch movie details"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _should_fetch_details(self, movie):
        """Check if we need to fetch additional details from TMDB"""
        if movie.type == "tv" and movie.season_number is None:
            return True
        return not (movie.plot and movie.rating and movie.genres.exists())

    def _fetch_movie_details(self, movie):
        """Fetch and update movie details from TMDB"""
        logger.debug(f"MovieDetailView: Fetching TMDB details for movie: {movie.title}")
        try:
            movie_info = None
            if movie.type == "movie":
                movie_info = tmdb_client.get_movie_details(movie.tmdb_id)
            elif movie.type == "tv":
                movie_info = tmdb_client.get_tv_details(movie.tmdb_id)
            movie = Movie.objects.update_from_tmdb_details(movie, movie_info)

            if movie_info.get("belongs_to_collection"):
                collection_id = movie_info["belongs_to_collection"]["id"]
                logger.info(f"MovieDetailView: Fetching collection {collection_id} for movie: {movie.title}")
                collection = self._fetch_collection_details(collection_id)
                movie.collection = collection
                movie.save()

            return movie
        except Exception as e:
            logger.error(f"MovieDetailView: Error fetching movie details: {str(e)}", exc_info=True)
            raise

    def _fetch_movie_credits(self, movie):
        """Fetch and update movie credits from TMDB"""
        logger.debug(f"MovieDetailView: Fetching credits for movie: {movie.title}")
        try:
            credits = None
            if movie.type == "movie":
                credits = tmdb_client.get_movie_credits(movie.tmdb_id)
            elif movie.type == "tv":
                credits = tmdb_client.get_tv_credits(movie.tmdb_id)

            pprint.pprint(credits.get("cast", [])[:25])
            print(len(credits.get("cast", [])))
            # Update cast
            for cast_member in credits.get("cast", [])[:25]:
                logger.debug(f"MovieDetailView: Processing cast member: {cast_member.get('name')}")
                person = Person.objects.create_or_update_from_tmdb(cast_member)
                MovieCast.objects.get_or_create(
                    movie=movie, person=person, defaults={"character": cast_member.get("character")}
                )

            # Update directors
            for crew_member in credits.get("crew", []):
                if crew_member["job"] == "Director":
                    logger.debug(f"MovieDetailView: Processing director: {crew_member.get('name')}")
                    person = Person.objects.create_or_update_from_tmdb(crew_member)
                    movie.directors.add(person)

        except Exception as e:
            logger.error(f"MovieDetailView: Error fetching movie credits: {str(e)}", exc_info=True)
            raise

    def _fetch_collection_details(self, collection_id):
        """Fetch collection details"""
        logger.debug(f"MovieDetailView: Fetching collection details for ID: {collection_id}")
        try:
            collection_data = tmdb_client.get_collection_details(collection_id)
            collection = Collection.objects.create_or_update_from_tmdb(collection_data)

            logger.debug(f"MovieDetailView: Processing {len(collection_data.get('parts', []))} movies in collection")
            for movie_data in collection_data.get("parts", []):
                movie = Movie.objects.create_or_update_from_tmdb(movie_data)
                movie.collection = collection
                movie.save()

            return collection
        except Exception as e:
            logger.error(f"MovieDetailView: Error fetching collection details: {str(e)}", exc_info=True)
            raise


class MovieDiscoverView(generics.ListAPIView):
    """Discover movies through different categories."""

    serializer_class = MovieListSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="Discover movies by category",
        manual_parameters=[
            openapi.Parameter(
                "category",
                openapi.IN_QUERY,
                description="Category of movies to fetch",
                type=openapi.TYPE_STRING,
                required=True,
                enum=["popular", "now_playing", "top_rated", "upcoming"],
            ),
            openapi.Parameter(
                "page", openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, default=1
            ),
        ],
        responses={200: MovieListSerializer(many=True), 400: "Bad Request - Invalid category"},
    )
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def get(self, request, *args, **kwargs):
        category = request.query_params.get("category", "popular")
        page = request.query_params.get("page", "1")

        logger.debug(f"MovieDiscoverView: Fetching {category} movies, page {page}")

        try:
            page = int(page)
            if page < 1:
                logger.warning(f"MovieDiscoverView: Invalid page number {page}, defaulting to 1")
                page = 1
        except ValueError:
            logger.warning(f"MovieDiscoverView: Invalid page value {page}, defaulting to 1")
            page = 1

        if category not in ["popular", "now_playing", "top_rated", "upcoming"]:
            logger.warning(f"MovieDiscoverView: Invalid category {category}, defaulting to 'popular'")
            category = "popular"

        try:
            movies = self._get_movies_by_category(category, page)
            serializer = self.get_serializer(movies, many=True)
            logger.info(f"MovieDiscoverView: Successfully fetched {len(movies)} {category} movies")
            return Response({"results": serializer.data, "category": category, "page": page})
        except Exception as e:
            logger.error(f"MovieDiscoverView: Error fetching movies: {str(e)}", exc_info=True)
            return Response({"results": [], "category": category, "page": page})

    def _get_movies_by_category(self, category, page=1):
        """Get movies based on category"""
        logger.debug(f"MovieDiscoverView: Fetching {category} movies from TMDB, page {page}")
        try:
            if category == "popular":
                results = tmdb_client.get_popular_movies(page)
            elif category == "now_playing":
                results = tmdb_client.get_now_playing_movies(page)
            elif category == "upcoming":
                results = tmdb_client.get_upcoming_movies(page)
            else:  # top_rated
                results = tmdb_client.get_top_rated_movies(page)

            movies = []
            for result in results:
                logger.debug(f"MovieDiscoverView: Processing movie: {result.get('title', 'Unknown')}")
                movie = Movie.objects.create_or_update_from_tmdb(result)
                movies.append(movie)

            return movies
        except Exception as e:
            logger.error(f"MovieDiscoverView: Error in _get_movies_by_category: {str(e)}", exc_info=True)
            raise


class WatchlistMoviesView(generics.ListAPIView):
    """List movies in user's watchlist filtered by status."""

    serializer_class = MovieListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @swagger_auto_schema(
        operation_description="Get movies in user's watchlist by status",
        manual_parameters=[
            openapi.Parameter(
                "search",
                openapi.IN_QUERY,
                description="Search term to filter movies by title",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "sort",
                openapi.IN_QUERY,
                description="Sort movies by",
                type=openapi.TYPE_STRING,
                required=False,
                enum=["date", "title", "rating"],
            ),
        ],
        responses={200: MovieListSerializer(many=True), 403: "Forbidden - Not authenticated"},
        security=[{"Token": []}],
    )
    def get(self, request, *args, **kwargs):
        status = self.kwargs.get("status")
        search_query = self.request.query_params.get("search", "")
        sort_by = self.request.query_params.get("sort", "-created_at")

        if status not in [s[0] for s in Watchlist.Statuses.choices]:
            raise ValidationError({"status": "Invalid status"})

        queryset = Watchlist.objects.get_user_watchlist(user=self.request.user, status=status)

        if search_query:
            queryset = queryset.filter(movie__title__icontains=search_query)

        # Apply sorting
        if sort_by == "title":
            queryset = queryset.order_by("movie__title")
        elif sort_by == "rating":
            queryset = queryset.order_by("-movie__rating")
        else:  # default to date
            queryset = queryset.order_by("-created_at")

        return [item.movie for item in queryset]


class MovieCommentsViewSet(viewsets.ModelViewSet):
    """ViewSet for handling movie comments."""

    serializer_class = CommentSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        movie_id = self.kwargs.get("movie_id")
        type = self.kwargs.get("type")
        return (
            Comment.objects.filter(movie__tmdb_id=movie_id, movie__type=type, parent__isnull=True)
            .prefetch_related("user", "responses", "responses__user", "likes")
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @swagger_auto_schema(
        operation_description="List comments for a movie",
        responses={200: CommentSerializer(many=True), 403: "Forbidden - Not authenticated"},
        security=[{"Token": []}],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Add a comment to a movie",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["content"],
            properties={
                "content": openapi.Schema(type=openapi.TYPE_STRING, description="Comment content"),
                "parent": openapi.Schema(type=openapi.TYPE_INTEGER, description="Parent comment ID for replies"),
            },
        ),
        responses={201: CommentSerializer, 400: "Bad Request - Invalid data", 403: "Forbidden - Not authenticated"},
        security=[{"Token": []}],
    )
    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Not authenticated"}, status=status.HTTP_403_FORBIDDEN)
        logger.info(f"MovieCommentsViewSet: Creating new comment for movie {kwargs.get('movie_id')}")
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"MovieCommentsViewSet: Error creating comment: {str(e)}", exc_info=True)
            raise

    @swagger_auto_schema(
        operation_description="Like or unlike a comment",
        responses={
            200: "Successfully liked/unliked comment",
            403: "Forbidden - Not authenticated",
            404: "Comment not found",
        },
        security=[{"Token": []}],
    )
    @action(detail=True, methods=["post"])
    def like(self, request, movie_id=None, type=None, pk=None):
        if not request.user.is_authenticated:
            return Response({"detail": "Not authenticated"}, status=status.HTTP_403_FORBIDDEN)
        logger.debug(f"MovieCommentsViewSet: Toggle like for comment {pk}")
        comment = self.get_object()
        user = request.user

        try:
            if user in comment.likes.all():
                logger.info(f"MovieCommentsViewSet: User {user.id} unliking comment {pk}")
                comment.likes.remove(user)
                return Response({"liked": False, "likes_count": comment.likes.count()})
            else:
                logger.info(f"MovieCommentsViewSet: User {user.id} liking comment {pk}")
                comment.likes.add(user)
                return Response({"liked": True, "likes_count": comment.likes.count()})
        except Exception as e:
            logger.error(f"MovieCommentsViewSet: Error toggling like: {str(e)}", exc_info=True)
            raise

    @swagger_auto_schema(
        operation_description="Reply to a comment",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["content"],
            properties={"content": openapi.Schema(type=openapi.TYPE_STRING, description="Reply content")},
        ),
        responses={
            201: CommentSerializer,
            400: "Bad Request - Invalid data",
            403: "Forbidden - Not authenticated",
            404: "Parent comment not found",
        },
        security=[{"Token": []}],
    )
    @action(detail=True, methods=["post"])
    def reply(self, request, movie_id=None, pk=None):
        if not request.user.is_authenticated:
            return Response({"detail": "Not authenticated"}, status=status.HTTP_403_FORBIDDEN)
        parent_comment = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user, movie_id=movie_id, parent=parent_comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MultiSearchView(generics.ListAPIView):
    """Search for movies, TV shows, and people using TMDB API."""

    serializer_class = MovieSerializer  # We'll need to create a new serializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="Search for movies, TV shows, and people using TMDB API",
        manual_parameters=[
            openapi.Parameter(
                "query", openapi.IN_QUERY, description="Search term", type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={200: MovieSerializer(many=True), 400: "Bad Request - Missing query parameter"},
    )
    def get(self, request, *args, **kwargs):
        query = request.query_params.get("query")
        logger.debug(f"ContentSearchView: Received search query: {query}")

        if not query:
            logger.warning("ContentSearchView: No query provided")
            raise ValidationError({"query": "Search query is required"})

        cache_key = f"content_search_{query}"
        cached_results = cache.get(cache_key)

        if cached_results is not None:
            logger.info(f"ContentSearchView: Returning cached results for query: {query}")
            return Response(cached_results)

        try:
            logger.info(f"ContentSearchView: Fetching results from TMDB for query: {query}")
            results = tmdb_client.search_multi(query)

            # save results
            for result in results.get("results")[:5]:
                if result.get("type") in ["movie", "tv"]:
                    Movie.objects.create_or_update_from_tmdb(result)

            logger.info(f"ContentSearchView: Caching results for query: {query}")
            cache.set(cache_key, results, timeout=3600)
            return Response(results)

        except Exception as e:
            logger.error(f"ContentSearchView: Error searching content: {str(e)}", exc_info=True)
            raise ValidationError({"detail": f"Failed to search content: {str(e)}"})


class EpisodeListView(generics.ListAPIView):
    serializer_class = EpisodeSerializer
    pagination_class = None
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self, *args, **kwargs):
        tmdb_id = int(self.kwargs.get("tmdb_id", 0))
        season_number = int(self.kwargs.get("season_number", 1))
        print(tmdb_id, "tmdb id")

        movie = get_object_or_404(Movie, tmdb_id=tmdb_id, type="tv")

        if Episode.objects.filter(movie=movie).count() < movie.episode_number:
            season_number = movie.season_number
            for season in range(1, season_number + 1):
                episodes = tmdb_client.get_tv_season_episodes(tmdb_id, season)
                for episode in episodes:
                    Episode.objects.create_or_update_from_tmdb(episode, movie=movie)

        return Episode.objects.filter(movie=movie, season_number=season_number)
