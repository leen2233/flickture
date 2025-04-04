from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MovieSearchView, MovieDetailView, CastListAPIView,
    PersonDetailView, PersonFilmographyListView, WatchlistAPIView, MovieDiscoverView,
    WatchlistMoviesView, FavoriteAPIView, MovieCommentsViewSet, ListViewSet, PersonFollowView,
    MultiSearchView
)

# ViewSet router
router = DefaultRouter()
router.register(
    'movies/(?P<movie_id>\\d+)/comments',
    MovieCommentsViewSet,
    basename='movie-comments'
)
router.register(r'lists', ListViewSet, basename='lists')

# API URLs
urlpatterns = [
    # Movie endpoints
    path('movies/search/', MovieSearchView.as_view(), name='movie-search'),
    path('movies/search/multi/', MultiSearchView.as_view(), name='movie-search-multi'),
    path('movies/discover/', MovieDiscoverView.as_view(), name='movie-discover'),
    path('movies/<str:tmdb_id>/<str:type>', MovieDetailView.as_view(), name='movie-detail'),
    path('movies/<str:tmdb_id>/cast/', CastListAPIView.as_view(), name='movie-cast'),

    # Person endpoints
    path('persons/<str:tmdb_id>/', PersonDetailView.as_view(), name='person-detail'),
    path('persons/<str:tmdb_id>/filmography/', PersonFilmographyListView.as_view(), name='person-filmography'),
    path('persons/<str:tmdb_id>/follow/', PersonFollowView.as_view(), name='person-follow'),

    # User collection endpoints
    path('watchlist/', WatchlistAPIView.as_view(), name='watchlist-list'),
    path('watchlist/<str:tmdb_id>/', WatchlistAPIView.as_view(), name='watchlist-detail'),
    path('watchlist/movies/<str:status>/', WatchlistMoviesView.as_view(), name='watchlist-movies'),
    path('favorites/', FavoriteAPIView.as_view(), name='favorites'),
    path('favorites/<str:tmdb_id>/', FavoriteAPIView.as_view(), name='favorite-detail'),

    # List endpoints
    path('lists/', ListViewSet.as_view({'get': 'list', 'post': 'create'}), name='list-list'),
    path('lists/<int:pk>/', ListViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='list-detail'),
]

# Include router URLs
urlpatterns += router.urls
