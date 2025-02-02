import requests
from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError, NotFound
from django.conf import settings
from django.db.models import Count, Q
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from datetime import datetime, timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.models import Favorite, Movie, Genre, MovieCast, Person, Collection, Watchlist, Comment
from core.serializers import (
    MovieSerializer, MovieDetailSerializer, MovieListSerializer,
    CommentSerializer, WatchlistSerializer
)
from core.utils.tmdb import TMDBClient

# Initialize TMDB client
tmdb_client = TMDBClient(api_key=settings.TMDB_API_KEY)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class for consistent pagination across views"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class MovieSearchView(generics.ListAPIView):
    """Search movies in local database by title."""
    serializer_class = MovieSerializer
    pagination_class = StandardResultsSetPagination

    @swagger_auto_schema(
        operation_description="Search for movies in the local database by title",
        manual_parameters=[
            openapi.Parameter(
                'query',
                openapi.IN_QUERY,
                description="Search term for movie title",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: MovieSerializer(many=True),
            400: 'Bad Request - Missing query parameter'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        query = self.request.query_params.get('query')
        if not query:
            return Movie.objects.none()
        return Movie.objects.filter(title__icontains=query)


class MovieSearchWidelyView(generics.ListAPIView):
    """Search movies using TMDB API and store results locally."""
    serializer_class = MovieSerializer
    pagination_class = StandardResultsSetPagination

    @swagger_auto_schema(
        operation_description="Search for movies using TMDB API (wider search scope)",
        manual_parameters=[
            openapi.Parameter(
                'query',
                openapi.IN_QUERY,
                description="Search term for movie title",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: MovieSerializer(many=True),
            400: 'Bad Request - Missing query parameter'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        query = self.request.query_params.get('query')
        if not query:
            raise ValidationError({'query': 'Search query is required'})

        cache_key = f'movie_search_{query}'
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            return cached_results

        try:
            results = tmdb_client.search_movies(query)
            movies = []

            for result in results:
                movie = Movie.objects.create_or_update_from_tmdb(result)
                movies.append(movie)

            cache.set(cache_key, movies, timeout=3600)  # Cache for 1 hour
            return movies

        except Exception as e:
            raise ValidationError({'detail': f'Failed to search movies: {str(e)}'})


class MovieDetailView(generics.RetrieveAPIView):
    """Retrieve detailed movie information."""
    queryset = Movie.objects.all()
    serializer_class = MovieDetailSerializer
    lookup_field = 'tmdb_id'

    def get_object(self):
        try:
            movie = Movie.objects.get(tmdb_id=self.kwargs['tmdb_id'])
            return movie
        except Movie.DoesNotExist:
            raise NotFound('Movie not found')

    @swagger_auto_schema(
        operation_description="Get detailed information about a specific movie",
        responses={
            200: MovieDetailSerializer,
            404: 'Movie not found'
        }
    )
    @method_decorator(cache_page(60 * 60 * 24))  # Cache for 24 hours
    def get(self, request, *args, **kwargs):
        try:
            movie = self.get_object()

            # Fetch additional details if needed
            if self._should_fetch_details(movie):
                movie = self._fetch_movie_details(movie)

            if not movie.cast.exists():
                self._fetch_movie_credits(movie)

            serializer = self.get_serializer(movie)
            return Response(serializer.data)

        except NotFound as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error in MovieDetailView: {str(e)}")
            return Response(
                {'detail': 'Failed to fetch movie details'},
                status=status.HTTP_404_NOT_FOUND
            )

    def _should_fetch_details(self, movie):
        """Check if we need to fetch additional details from TMDB"""
        return not (movie.plot and movie.rating and movie.genres.exists())

    def _fetch_movie_details(self, movie):
        """Fetch and update movie details from TMDB"""
        movie_info = tmdb_client.get_movie_details(movie.tmdb_id)
        movie = Movie.objects.update_from_tmdb_details(movie, movie_info)

        if movie_info.get('belongs_to_collection'):
            collection = Collection.objects.create_or_update_from_tmdb(
                movie_info['belongs_to_collection']['id']
            )
            movie.collection = collection
            movie.save()

        return movie

    def _fetch_movie_credits(self, movie):
        """Fetch and update movie credits from TMDB"""
        credits = tmdb_client.get_movie_credits(movie.tmdb_id)

        # Update cast
        for cast_member in credits.get('cast', [])[:10]:
            person = Person.objects.create_or_update_from_tmdb(cast_member)
            MovieCast.objects.get_or_create(
                movie=movie,
                person=person,
                defaults={'character': cast_member.get('character')}
            )

        # Update directors
        for crew_member in credits.get('crew', []):
            if crew_member['job'] == 'Director':
                person = Person.objects.create_or_update_from_tmdb(crew_member)
                movie.directors.add(person)


class MovieDiscoverView(generics.ListAPIView):
    """Discover movies through different categories."""
    serializer_class = MovieListSerializer
    pagination_class = StandardResultsSetPagination

    @swagger_auto_schema(
        operation_description="Discover movies by category",
        manual_parameters=[
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="Category of movies to fetch",
                type=openapi.TYPE_STRING,
                required=True,
                enum=['popular', 'now_playing', 'top_rated']
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number",
                type=openapi.TYPE_INTEGER,
                default=1
            )
        ],
        responses={
            200: MovieListSerializer(many=True),
            400: 'Bad Request - Invalid category'
        }
    )
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def get(self, request, *args, **kwargs):
        category = request.query_params.get('category', 'popular')
        page = request.query_params.get('page', '1')

        try:
            page = int(page)
            if page < 1:
                page = 1
        except ValueError:
            page = 1

        # Default to 'popular' for invalid categories
        if category not in ['popular', 'now_playing', 'top_rated']:
            category = 'popular'

        try:
            movies = self._get_movies_by_category(category, page)
            serializer = self.get_serializer(movies, many=True)
            return Response({
                'results': serializer.data,
                'category': category,
                'page': page
            })
        except Exception as e:
            # Log the error for debugging
            print(f"Error in MovieDiscoverView: {str(e)}")
            # Default to empty results instead of error
            return Response({
                'results': [],
                'category': category,
                'page': page
            })

    def _get_movies_by_category(self, category, page=1):
        """Get movies based on category"""
        try:
            if category == 'popular':
                results = tmdb_client.get_popular_movies(page)
            elif category == 'now_playing':
                results = tmdb_client.get_now_playing_movies(page)
            else:  # top_rated
                results = tmdb_client.get_top_rated_movies(page)

            movies = []
            for result in results:
                movie = Movie.objects.create_or_update_from_tmdb(result)
                movies.append(movie)

            return movies
        except Exception as e:
            # Log the error for debugging
            print(f"Error in _get_movies_by_category: {str(e)}")
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
                'search',
                openapi.IN_QUERY,
                description="Search term to filter movies by title",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'sort',
                openapi.IN_QUERY,
                description="Sort movies by",
                type=openapi.TYPE_STRING,
                required=False,
                enum=['date', 'title', 'rating']
            )
        ],
        responses={
            200: MovieListSerializer(many=True),
            403: 'Forbidden - Not authenticated'
        },
        security=[{'Token': []}]
    )
    def get(self, request, *args, **kwargs):
        status = self.kwargs.get('status')
        search_query = self.request.query_params.get('search', '')
        sort_by = self.request.query_params.get('sort', '-created_at')

        if status not in [s[0] for s in Watchlist.Statuses.choices]:
            raise ValidationError({'status': 'Invalid status'})

        queryset = Watchlist.objects.get_user_watchlist(
            user=self.request.user,
            status=status
        )

        if search_query:
            queryset = queryset.filter(movie__title__icontains=search_query)

        # Apply sorting
        if sort_by == 'title':
            queryset = queryset.order_by('movie__title')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-movie__rating')
        else:  # default to date
            queryset = queryset.order_by('-created_at')

        return [item.movie for item in queryset]


class MovieCommentsViewSet(viewsets.ModelViewSet):
    """ViewSet for handling movie comments."""
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        movie_id = self.kwargs.get('movie_id')
        return Comment.objects.filter(
            movie_id=movie_id,
            parent__isnull=True
        ).prefetch_related(
            'user',
            'responses',
            'responses__user',
            'likes'
        ).order_by('-created_at')

    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @swagger_auto_schema(
        operation_description="List comments for a movie",
        responses={
            200: CommentSerializer(many=True),
            403: 'Forbidden - Not authenticated'
        },
        security=[{'Token': []}]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Add a comment to a movie",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['content'],
            properties={
                'content': openapi.Schema(type=openapi.TYPE_STRING, description='Comment content'),
                'parent': openapi.Schema(type=openapi.TYPE_INTEGER, description='Parent comment ID for replies')
            }
        ),
        responses={
            201: CommentSerializer,
            400: 'Bad Request - Invalid data',
            403: 'Forbidden - Not authenticated'
        },
        security=[{'Token': []}]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Like or unlike a comment",
        responses={
            200: 'Successfully liked/unliked comment',
            403: 'Forbidden - Not authenticated',
            404: 'Comment not found'
        },
        security=[{'Token': []}]
    )
    @action(detail=True, methods=['post'])
    def like(self, request, movie_id=None, pk=None):
        comment = self.get_object()
        user = request.user

        if user in comment.likes.all():
            comment.likes.remove(user)
            return Response({'detail': 'Comment unliked'})
        else:
            comment.likes.add(user)
            return Response({'detail': 'Comment liked'})

    @swagger_auto_schema(
        operation_description="Reply to a comment",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['content'],
            properties={
                'content': openapi.Schema(type=openapi.TYPE_STRING, description='Reply content')
            }
        ),
        responses={
            201: CommentSerializer,
            400: 'Bad Request - Invalid data',
            403: 'Forbidden - Not authenticated',
            404: 'Parent comment not found'
        },
        security=[{'Token': []}]
    )
    @action(detail=True, methods=['post'])
    def reply(self, request, movie_id=None, pk=None):
        parent_comment = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save(
                user=request.user,
                movie_id=movie_id,
                parent=parent_comment
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
