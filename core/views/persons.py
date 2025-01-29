from imdb import Cinemagoer
from rest_framework import generics, status
from rest_framework.response import Response

from core.models import Person, Movie
from core.serializers import PersonSerializer, MovieSerializer

ia = Cinemagoer()


class CastListAPIView(generics.ListAPIView):
    serializer_class = PersonSerializer

    def get_queryset(self):
        movie_id = self.kwargs.get('movie_id')
        return Person.objects.filter(acted_movies__imdb_id=movie_id)


class PersonDetailView(generics.RetrieveAPIView):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    lookup_field = 'imdb_id'  # Assuming the lookup field is imdb_id

    def get(self, request, *args, **kwargs):
        person = self.get_object()  # Get the person object based on imdb_id

        if not person.headshot:
            # Fetch details from Cinemagoer using the imdb_id
            person_data = ia.get_person(person.imdb_id)
            filmography = person_data.__dict__.get("titlesRefs").values()
            for movie in filmography:
                movie_id = movie.__dict__.get("movieID")

                movie_obj, created = Movie.objects.get_or_create(
                    imdb_id=movie_id,
                    defaults={
                        'title': movie.get('title'),
                        'plot': movie.get('plot', ''),
                        'rating': movie.get('rating', 0),
                        'year': movie.get('year', 0),
                        'poster_preview_url': movie.get("cover url", ''),
                        'poster_url': movie.get("full-size cover url"),
                        'kind': movie.get('kind', ''),
                    }
                )
                movie_obj.cast.add(person)
            if 'headshot' in person_data:
                person.headshot = person_data.get('headshot')
            person.save()  # Save the updated person details

        serializer = self.get_serializer(person)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PersonFilmographyListView(generics.ListAPIView):
    serializer_class = MovieSerializer
    lookup_field = 'imdb_id'

    def get_queryset(self):
        person_id = self.kwargs.get('imdb_id')
        return Movie.objects.filter(cast__imdb_id=person_id)
