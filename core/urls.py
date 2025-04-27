from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CastListAPIView,
    CollectionDetailAPIView,
    EpisodeListView,
    FavoriteAPIView,
    FeedView,
    GenreListView,
    GenreMoviesView,
    ListViewSet,
    MovieCommentsViewSet,
    MovieDetailView,
    MovieDiscoverView,
    MultiSearchView,
    PersonDetailView,
    PersonFilmographyListView,
    PersonFollowView,
    WatchlistAPIView,
    WatchlistMoviesView,
)

# ViewSet router
router = DefaultRouter()
router.register("movies/(?P<movie_id>\\d+)/(?P<type>[^/]+)/comments", MovieCommentsViewSet, basename="movie-comments")
router.register(r"lists", ListViewSet, basename="lists")

# API URLs
urlpatterns = [
    # Movie endpoints
    path("movies/search/multi/", MultiSearchView.as_view(), name="movie-search-multi"),
    path("movies/discover/", MovieDiscoverView.as_view(), name="movie-discover"),
    path("movies/<str:tmdb_id>/<str:type>", MovieDetailView.as_view(), name="movie-detail"),
    path("movies/<str:tmdb_id>/<str:type>/cast/", CastListAPIView.as_view(), name="movie-cast"),
    path("movies/<str:tmdb_id>/season/<int:season_number>", EpisodeListView.as_view(), name="movie-season-details"),
    # Genre endpoints
    path("genres/", GenreListView.as_view(), name="genre-list"),
    path("genres/<str:genre_id>/movies/", GenreMoviesView.as_view(), name="genre-movies"),
    # Person endpoints
    path("persons/<str:tmdb_id>/", PersonDetailView.as_view(), name="person-detail"),
    path("persons/<str:tmdb_id>/filmography/", PersonFilmographyListView.as_view(), name="person-filmography"),
    path("persons/<str:tmdb_id>/follow/", PersonFollowView.as_view(), name="person-follow"),
    # User collection endpoints
    path("watchlist/", WatchlistAPIView.as_view(), name="watchlist-list"),
    path("watchlist/<str:type>/<str:tmdb_id>/", WatchlistAPIView.as_view(), name="watchlist-detail"),
    path("watchlist/movies/<str:status>/", WatchlistMoviesView.as_view(), name="watchlist-movies"),
    path("favorites/", FavoriteAPIView.as_view(), name="favorites"),
    path("favorites/<str:type>/<str:tmdb_id>/", FavoriteAPIView.as_view(), name="favorite-detail"),
    # collection endpoints
    path("collections/<str:tmdb_id>/", CollectionDetailAPIView.as_view(), name="collection-detail"),
    # feed endpoints
    path("feed/", FeedView.as_view(), name="feed"),
]

# Include router URLs
urlpatterns += router.urls
