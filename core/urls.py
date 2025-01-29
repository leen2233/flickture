from django.urls import path
from .views import MovieSearchView, MovieSearchWidelyView, MovieDetailView, CastListAPIView, PersonDetailView, \
    PersonFilmographyListView, WatchlistAPIView

urlpatterns = [
    path('search/', MovieSearchView.as_view(), name='movie-search'),
    path('search-widely/', MovieSearchWidelyView.as_view(), name='movie-search-widely'),
    path('<str:imdb_id>/detail', MovieDetailView.as_view(), name='movie-detail'),
    path('<str:movie_id>/cast', CastListAPIView.as_view(), name="movie-cast"),
    path('persons/<str:imdb_id>/detail', PersonDetailView.as_view(), name="person-detail"),
    path('persons/<str:imdb_id>/filmography', PersonFilmographyListView.as_view(), name="person-filmography"),
    path("watchlist", WatchlistAPIView.as_view(), name="watchlist")
]
