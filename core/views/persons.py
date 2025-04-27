import logging

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Movie, MovieCast, Person, PersonFollower
from core.serializers import MovieCastSerializer, MovieSerializer, PersonSerializer
from core.utils.tmdb import TMDBClient

# Configure logger
logger = logging.getLogger(__name__)

tmdb_client = TMDBClient(settings.TMDB_API_KEY)


class CastListAPIView(generics.ListAPIView):
    """API view for retrieving the cast of a movie."""

    serializer_class = MovieCastSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        tmdb_id = self.kwargs.get("tmdb_id")
        type = self.kwargs.get("type")
        movie = get_object_or_404(Movie, tmdb_id=tmdb_id, type=type)
        logger.info(f"CastListAPIView: Getting cast list for movie {tmdb_id}")
        return movie.cast.all()


class PersonDetailView(generics.RetrieveAPIView):
    """API view for retrieving detailed information about a person."""

    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "tmdb_id"

    def get_object(self):
        tmdb_id = self.kwargs["tmdb_id"]
        try:
            logger.debug(f"PersonDetailView: Fetching person with TMDB ID: {tmdb_id}")
            person = Person.objects.get(tmdb_id=tmdb_id)
            return person
        except Person.DoesNotExist:
            logger.info(f"PersonDetailView: Person not found locally with TMDB ID: {tmdb_id}, fetching from TMDB")
            try:
                person_info = tmdb_client.get_person_details(tmdb_id)

                person = Person.objects.create_or_update_from_tmdb(person_info)
                return person
            except Exception as e:
                logger.error(f"PersonDetailView: Failed to fetch person from TMDB: {str(e)}", exc_info=True)
                raise NotFound("Person not found on TMDB")

    @swagger_auto_schema(
        operation_description="Get detailed information about a person, including their filmography",
        responses={200: PersonSerializer, 404: "Person not found"},
    )
    def get(self, request, *args, **kwargs):
        try:
            person = self.get_object()
            logger.debug(f"PersonDetailView: Fetching details for person {person.name} (ID: {person.tmdb_id})")

            cache_key = f"person_details_{person.tmdb_id}"
            cached_data = cache.get(cache_key)

            if cached_data:
                logger.info(f"PersonDetailView: Returning cached data for person {person.tmdb_id}")
                return Response(cached_data)

            # Fetch person's movie credits
            logger.debug(f"PersonDetailView: Fetching credits for person {person.tmdb_id}")
            credits_data = tmdb_client.get_person_credits(person.tmdb_id)

            # Process cast credits
            if credits_data.get("cast"):
                logger.info(f"PersonDetailView: Processing {len(credits_data['cast'])} cast credits")
                for movie_data in credits_data["cast"]:
                    logger.debug(f"PersonDetailView: Processing cast credit for movie {movie_data.get('title')}")
                    movie = Movie.objects.create_or_update_from_tmdb(movie_data)
                    MovieCast.objects.get_or_create(
                        movie=movie, person=person, defaults={"character": movie_data.get("character")}
                    )

            # Process crew credits (for directors)
            if credits_data.get("crew"):
                logger.info("PersonDetailView: Processing crew credits")
                for movie_data in credits_data["crew"]:
                    if movie_data.get("job") == "Director":
                        logger.debug(
                            f"PersonDetailView: Processing director credit for movie {movie_data.get('title')}"
                        )
                        movie = Movie.objects.create_or_update_from_tmdb(movie_data)
                        movie.directors.add(person)

            serializer = self.get_serializer(person)
            logger.info(f"PersonDetailView: Caching data for person {person.tmdb_id}")
            cache.set(cache_key, serializer.data, timeout=60 * 60 * 24)  # Cache for 24 hours
            return Response(serializer.data)

        except Person.DoesNotExist:
            logger.warning(f"PersonDetailView: Person not found with ID {kwargs.get('tmdb_id')}")
            return Response({"error": "Person not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"PersonDetailView: Error fetching person details: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PersonFilmographyListView(generics.ListAPIView):
    """API view for retrieving a person's filmography."""

    serializer_class = MovieSerializer
    lookup_field = "tmdb_id"
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Get the complete filmography of a person",
        responses={200: MovieSerializer(many=True), 404: "Person not found"},
    )
    def get(self, request, *args, **kwargs):
        logger.debug(f"PersonFilmographyListView: Fetching filmography for person {kwargs.get('tmdb_id')}")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        person_id = self.kwargs.get("tmdb_id")
        try:
            logger.info(f"PersonFilmographyListView: Getting filmography for person {person_id}")
            person = Person.objects.get(tmdb_id=person_id)
            # Get both acted and directed movies
            return (
                Movie.objects.filter(models.Q(cast__person=person) | models.Q(directors=person))
                .distinct()
                .order_by("-popularity", "-year")
            )
        except Person.DoesNotExist:
            logger.warning(f"PersonFilmographyListView: Person not found with ID {person_id}")
            return Movie.objects.none()
        except Exception as e:
            logger.error(f"PersonFilmographyListView: Error getting filmography: {str(e)}", exc_info=True)
            return Movie.objects.none()


class PersonFollowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, tmdb_id):
        logger.debug(f"PersonFollowView: User {request.user.id} attempting to follow person {tmdb_id}")
        try:
            person = get_object_or_404(Person, tmdb_id=tmdb_id)
            follower, created = PersonFollower.objects.get_or_create(user=request.user, person=person)
            if created:
                logger.info(f"PersonFollowView: User {request.user.id} followed person {tmdb_id}")
                return Response({"status": "following"}, status=status.HTTP_201_CREATED)
            logger.info(f"PersonFollowView: User {request.user.id} already following person {tmdb_id}")
            return Response({"status": "already following"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"PersonFollowView: Error in follow operation: {str(e)}", exc_info=True)
            raise

    def delete(self, request, tmdb_id):
        logger.debug(f"PersonFollowView: User {request.user.id} attempting to unfollow person {tmdb_id}")
        try:
            person = get_object_or_404(Person, tmdb_id=tmdb_id)
            follower = PersonFollower.objects.get(user=request.user, person=person)
            follower.delete()
            logger.info(f"PersonFollowView: User {request.user.id} unfollowed person {tmdb_id}")
            return Response({"status": "unfollowed"}, status=status.HTTP_200_OK)
        except PersonFollower.DoesNotExist:
            logger.warning(f"PersonFollowView: User {request.user.id} was not following person {tmdb_id}")
            return Response({"status": "not following"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"PersonFollowView: Error in unfollow operation: {str(e)}", exc_info=True)
            raise

    def get(self, request, tmdb_id):
        logger.debug(f"PersonFollowView: Checking follow status for user {request.user.id} and person {tmdb_id}")
        try:
            person = get_object_or_404(Person, tmdb_id=tmdb_id)
            is_following = PersonFollower.objects.filter(user=request.user, person=person).exists()
            followers_count = person.followers.count()
            logger.info(f"PersonFollowView: Follow status retrieved for person {tmdb_id}")
            return Response({"is_following": is_following, "followers_count": followers_count})
        except Exception as e:
            logger.error(f"PersonFollowView: Error getting follow status: {str(e)}", exc_info=True)
            raise
