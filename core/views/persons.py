from django.conf import settings
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.db import models
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q

from core.models import MovieCast, Person, Movie, PersonFollower
from core.serializers import PersonSerializer, MovieSerializer
from core.utils.tmdb import TMDBClient

tmdb_client = TMDBClient(settings.TMDB_API_KEY)


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
        return Person.objects.filter(acted_movies__tmdb_id=movie_id)


class PersonDetailView(generics.RetrieveAPIView):
    """API view for retrieving detailed information about a person."""
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'tmdb_id'

    @swagger_auto_schema(
        operation_description="Get detailed information about a person, including their filmography",
        responses={
            200: PersonSerializer,
            404: 'Person not found'
        }
    )
    def get(self, request, *args, **kwargs):
        # try:
        person = self.get_object()
        cache_key = f'person_details_{person.tmdb_id}'
        cached_data = cache.get(cache_key)
        print(cached_data)
        if cached_data:
            return Response(cached_data)

        # Fetch person details from TMDB
        person_data = tmdb_client.get_person_details(person.tmdb_id)
        person = Person.objects.create_or_update_from_tmdb(person_data)

        # Fetch person's movie credits
        credits_data = tmdb_client.get_person_credits(person.tmdb_id)

        # Process cast credits
        if credits_data.get('cast'):
            for movie_data in credits_data['cast']:
                movie = Movie.objects.create_or_update_from_tmdb(movie_data)
                MovieCast.objects.get_or_create(
                    movie=movie,
                    person=person,
                    character=movie_data.get('character')
                )

        # Process crew credits (for directors)
        if credits_data.get('crew'):
            for movie_data in credits_data['crew']:
                if movie_data.get('job') == 'Director':
                    movie = Movie.objects.create_or_update_from_tmdb(movie_data)
                    movie.directors.add(person)

        serializer = self.get_serializer(person)
        cache.set(cache_key, serializer.data, timeout=60 * 60 * 24)  # Cache for 24 hours
        return Response(serializer.data)

        # except Person.DoesNotExist:
        #     return Response({'error': 'Person not found'}, status=status.HTTP_404_NOT_FOUND)
        # except Exception as e:
        #     return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PersonFilmographyListView(generics.ListAPIView):
    """API view for retrieving a person's filmography."""
    serializer_class = MovieSerializer
    lookup_field = 'tmdb_id'
    permission_classes = [permissions.AllowAny]

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
        person_id = self.kwargs.get('tmdb_id')
        try:
            person = Person.objects.get(tmdb_id=person_id)
            # Get both acted and directed movies
            return Movie.objects.filter(
                models.Q(cast__person=person) | models.Q(directors=person)
            ).distinct().order_by('-year', '-popularity')
        except Person.DoesNotExist:
            return Movie.objects.none()


class PersonFollowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, tmdb_id):
        person = get_object_or_404(Person, tmdb_id=tmdb_id)
        follower, created = PersonFollower.objects.get_or_create(
            user=request.user,
            person=person
        )
        if created:
            return Response({'status': 'following'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'already following'}, status=status.HTTP_200_OK)

    def delete(self, request, tmdb_id):
        person = get_object_or_404(Person, tmdb_id=tmdb_id)
        try:
            follower = PersonFollower.objects.get(user=request.user, person=person)
            follower.delete()
            return Response({'status': 'unfollowed'}, status=status.HTTP_200_OK)
        except PersonFollower.DoesNotExist:
            return Response({'status': 'not following'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, tmdb_id):
        person = get_object_or_404(Person, tmdb_id=tmdb_id)
        is_following = PersonFollower.objects.filter(
            user=request.user,
            person=person
        ).exists()
        return Response({
            'is_following': is_following,
            'followers_count': person.followers.count()
        })
