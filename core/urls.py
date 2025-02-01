from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MovieSearchView, MovieSearchWidelyView, MovieDetailView, CastListAPIView,
    PersonDetailView, PersonFilmographyListView, WatchlistAPIView, MovieListsView,
    MovieListView, FavoriteAPIView, MovieCommentsViewSet, toggle_comment_like
)

router = DefaultRouter()
router.register(r'movies/(?P<movie_id>\d+)/comments', MovieCommentsViewSet, basename='movie-comments')

urlpatterns = [
    path('search/', MovieSearchView.as_view(), name='movie-search'),
    path('search-widely/', MovieSearchWidelyView.as_view(), name='movie-search-widely'),
    path('movies/<str:tmdb_id>/detail/', MovieDetailView.as_view(), name='movie-detail'),
    path('movies/<str:tmdb_id>/cast/', CastListAPIView.as_view(), name='movie-cast'),
    path('person/<str:person_id>/', PersonDetailView.as_view(), name='person-detail'),
    path('person/<str:person_id>/filmography/', PersonFilmographyListView.as_view(), name='person-filmography'),
    path('movies/watchlist/', WatchlistAPIView.as_view(), name='watchlist'),
    path('movies/watchlist/<str:tmdb_id>/', WatchlistAPIView.as_view(), name='watchlist-detail'),
    path('movies/lists/', MovieListsView.as_view(), name='movie-lists'),
    path('movies/lists/<str:list_type>/', MovieListView.as_view(), name='movie-list'),
    path("favorites/", FavoriteAPIView.as_view(), name="favorites"),
    path("favorites/<str:tmdb_id>/", FavoriteAPIView.as_view(), name="favorite-detail"),
    path('comments/<int:comment_id>/like/', toggle_comment_like, name='toggle-comment-like'),
]

urlpatterns += router.urls
