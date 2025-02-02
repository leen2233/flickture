from imdb import Cinemagoer
from rest_framework import generics, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.models import Person, Movie
from core.serializers import PersonSerializer, MovieSerializer

ia = Cinemagoer()


class CastListAPIView(generics.ListAPIView):
    """API view for retrieving the cast of a movie."""
    serializer_class = PersonSerializer

    @swagger_auto_schema(
        operation_description="Get the cast list for a specific movie",
        responses={
            200: PersonSerializer(many=True),
            404: 'Movie not found'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        movie_id = self.kwargs.get('movie_id')
        return Person.objects.filter(acted_movies__imdb_id=movie_id)


class PersonDetailView(generics.RetrieveAPIView):
    """API view for retrieving detailed information about a person."""
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    lookup_field = 'imdb_id'

    @swagger_auto_schema(
        operation_description="Get detailed information about a person, including their filmography",
        responses={
            200: PersonSerializer,
            404: 'Person not found'
        }
    )
    def get(self, request, *args, **kwargs):
        person = self.get_object()

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
            person.save()

        serializer = self.get_serializer(person)
        return Response(serializer.data)


class PersonFilmographyListView(generics.ListAPIView):
    """API view for retrieving a person's filmography."""
    serializer_class = MovieSerializer
    lookup_field = 'imdb_id'

    @swagger_auto_schema(
        operation_description="Get the complete filmography of a person",
        responses={
            200: MovieSerializer(many=True),
            404: 'Person not found'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        person_id = self.kwargs.get('imdb_id')
        try:
            person = Person.objects.get(imdb_id=person_id)
            return Movie.objects.filter(cast=person).order_by('-year')
        except Person.DoesNotExist:
            return Movie.objects.none()
