from django.urls import path
from .views import MovieSearchView, MovieSearchWidelyView, MovieDetailView

urlpatterns = [
    path('search/', MovieSearchView.as_view(), name='movie-search'),
    path('search-widely/', MovieSearchWidelyView.as_view(), name='movie-search-widely'),
    path('detail/<str:imdb_id>', MovieDetailView.as_view(), name='movie-detail'),
]
