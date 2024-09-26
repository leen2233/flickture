from django.shortcuts import render

# Create your views here.
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .models import Movie, Genre, Person
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
                movie_id = result.__dict__.get("movieID")
                # Check if movie exists in the database
                movie, created = Movie.objects.get_or_create(
                    imdb_id=movie_id,
                    defaults={
                        'title': result.get('title'),
                        'plot': result.get('plot', ''),
                        'rating': result.get('rating', 0),
                        'year': result.get('year', 0),
                        'poster_url': result.get("cover url", ''),
                        'poster_preview_url': result.get("full-size cover url"),
                        'kind': result.get('kind', ''),
                    }
                )
                movies_created.append(movie)

            # Serialize the results
            serializer = self.get_serializer(movies_created, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({'detail': 'Title parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)


class MovieDetailView(generics.RetrieveAPIView):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    lookup_field = 'imdb_id'  # Assuming the lookup field is imdb_id

    def get(self, request, *args, **kwargs):
        movie = self.get_object()  # Get the movie object based on imdb_id

        # Check if rating or plot is missing
        if not movie.rating or not movie.plot:
            # Fetch details from Cinemagoer using the imdb_id
            movie_data = ia.get_movie(movie.imdb_id)
            # print(movie_data.infoset2keys)
            if not movie.plot and 'plot' in movie_data:
                movie.plot = movie_data.get('plot', [''])[0]  # Use the first plot summary if available
            if not movie.rating and 'rating' in movie_data:
                movie.rating = movie_data.get('rating', 0)
            genres = movie_data.get("genres")
            for genre in genres:
                genre_obj, created = Genre.objects.get_or_create(name=genre)
                movie.genres.add(genre_obj)
            cast = movie_data.get("cast")
            for person in cast:
                person_obj, created = Person.objects.get_or_create(name=person.get("name"),
                                                          imdb_id=person.__dict__.get("personID"))
                movie.cast.add(person_obj)
            # print(movie_data.__dict__)
            if movie_data.get("director"):
                directors = movie_data.get("director")
            else:
                directors = movie_data.get("writer")
            if directors:
                for director in directors:
                    person_obj, created = Person.objects.get_or_create(name=director.get("name"),
                                                                       imdb_id=director.__dict__.get("personID"))
                    movie.directors.add(person_obj)

            movie.save()  # Save the updated movie details

        serializer = self.get_serializer(movie)
        return Response(serializer.data, status=status.HTTP_200_OK)