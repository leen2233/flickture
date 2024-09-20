from django.urls import path
from .views import MovieSearchView, MovieSearchWidelyView

urlpatterns = [
    path('search/', MovieSearchView.as_view(), name='movie-search'),
    path('search-widely/', MovieSearchWidelyView.as_view(), name='movie-search-widely'),
]
