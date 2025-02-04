from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MovieSearchView, MovieSearchWidelyView, MovieDetailView, CastListAPIView,
    PersonDetailView, PersonFilmographyListView, WatchlistAPIView, MovieDiscoverView,
    WatchlistMoviesView, FavoriteAPIView, MovieCommentsViewSet
)

# ViewSet router
router = DefaultRouter()
router.register(
    'movies/(?P<movie_id>\\d+)/comments',
    MovieCommentsViewSet,
    basename='movie-comments'
)

# API URLs
urlpatterns = [
    # Movie endpoints
    path('movies/search', MovieSearchView.as_view(), name='movie-search'),
    path('movies/search/widely', MovieSearchWidelyView.as_view(), name='movie-search-widely'),
    path('movies/discover', MovieDiscoverView.as_view(), name='movie-discover'),
    path('movies/<str:tmdb_id>', MovieDetailView.as_view(), name='movie-detail'),
    path('movies/<str:tmdb_id>/cast', CastListAPIView.as_view(), name='movie-cast'),

    # Person endpoints
    path('persons/<str:person_id>', PersonDetailView.as_view(), name='person-detail'),
    path('persons/<str:person_id>/filmography', PersonFilmographyListView.as_view(), name='person-filmography'),

    # User collection endpoints
    path('watchlist', WatchlistAPIView.as_view(), name='watchlist'),
    path('watchlist/<str:tmdb_id>', WatchlistAPIView.as_view(), name='watchlist-detail'),
    path('watchlist/movies/<str:status>', WatchlistMoviesView.as_view(), name='watchlist-movies'),
    path('favorites', FavoriteAPIView.as_view(), name='favorites'),
    path('favorites/<str:tmdb_id>', FavoriteAPIView.as_view(), name='favorite-detail'),
]

# Include router URLs
urlpatterns += router.urls
