from django.shortcuts import render

# Create your views here.
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .models import Movie
from .serializers import MovieSerializer
from imdb import Cinemagoer

ia = Cinemagoer()


class MovieSearchView(generics.ListAPIView):
    serializer_class = MovieSerializer

    def get_queryset(self):
        title = self.request.query_params.get('title', None)
        if title:
            return Movie.objects.filter(title__icontains=title)
        return Movie.objects.none()


class MovieSearchWidelyView(generics.GenericAPIView):
    serializer_class = MovieSerializer

    def get(self, request):
        title = request.query_params.get('title', None)
        if title:
            # Search in Cinemagoer
            search_results = ia.search_movie(title)
            movies_created = []

            for result in search_results:
                print(result.__dict__)
                movie_id = result.__dict__.get("movieID")
                # Check if movie exists in the database
                movie, created = Movie.objects.get_or_create(
                    imdb_id=movie_id,
                    defaults={
                        'title': result.get('title'),
                        'plot': result.get('plot', ''),
                        'rating': result.get('rating', 0),
                        'year': result.get('year', 0),
                        'cover_url': result.get('cover url', ''),
                        'kind': result.get('kind', ''),
                    }
                )
                if created:
                    movies_created.append(movie)

            # Serialize the results
            serializer = self.get_serializer(movies_created, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({'detail': 'Title parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)
