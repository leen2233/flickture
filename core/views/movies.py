import requests
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from core.models import Movie, Genre, MovieCast, Person, Collection, Watchlist
from core.serializers import MovieSerializer, MovieDetailSerializer, WatchlistMoviesSerializer
from tmdbv3api import TMDb, Movie as TMDBMovie, Search, Genre as TMDBGenre, Collection as TMDBCollection
from django.conf import settings
from django.db.models import Count
from datetime import datetime, timedelta

# Configure TMDB
tmdb = TMDb()
tmdb.api_key = settings.TMDB_API_KEY
tmdb.language = 'en'
tmdb.debug = True


class MovieSearchView(generics.ListAPIView):
    serializer_class = MovieSerializer

    def get_queryset(self):
        title = self.request.query_params.get('query', None)
        if title:
            return Movie.objects.filter(title__icontains=title)
        return Movie.objects.none()


class MovieSearchWidelyView(generics.GenericAPIView):
    serializer_class = MovieSerializer

    def get(self, request):
        query = request.query_params.get('query', None)
        if not query:
            return Response(
                {'detail': 'Query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Search movies using TMDB
            print("Searching for movies...")
            search = Search()
            results = search.movies(query)

            movies_created = []
            for result in results:
                # Get poster paths
                poster_path = result.poster_path
                backdrop_path = result.backdrop_path

                # Construct full poster URLs
                poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None
                poster_preview_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                backdrop_url = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else None

                # Create or update movie in database
                movie, created = Movie.objects.get_or_create(
                    tmdb_id=result.id,
                    defaults={
                        'title': result.title,
                        'plot': result.overview,
                        'rating': result.vote_average,
                        'poster_url': poster_url,
                        'poster_preview_url': poster_preview_url,
                        'backdrop_url': backdrop_url,
                        'year': result.release_date[:4] if hasattr(result, 'release_date') and result.release_date else None,
                        'popularity': getattr(result, 'popularity', 0),
                        'vote_count': getattr(result, 'vote_count', 0),
                    }
                )

                # if created:
                #     if poster_url:
                #         response = requests.get(poster_url)
                #         if response.status_code == 200:
                #             movie.photo.save(
                #                 f"person_photo_{person_data['imdb_id']}.jpg",
                #                 File(io.BytesIO(response.content)),
                #                 save=True
                #             )

                movies_created.append(movie)

            serializer = self.get_serializer(movies_created, many=True)
            return Response({
                'results': serializer.data,
                'total_results': len(movies_created),
                'page': 1
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'detail': f'Failed to search movies: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MovieDetailView(generics.RetrieveAPIView):
    queryset = Movie.objects.all()
    serializer_class = MovieDetailSerializer
    lookup_field = 'tmdb_id'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get(self, request, *args, **kwargs):
        movie = self.get_object()
        tmdb_movie = TMDBMovie()

        # Check if we need to fetch additional details
        if not movie.plot or not movie.rating or not movie.genres.exists():
            try:
                # Get detailed movie info from TMDB
                movie_info = tmdb_movie.details(movie.tmdb_id)

                # Update movie details
                movie.title = movie_info.title
                movie.plot = movie_info.overview
                movie.rating = movie_info.vote_average
                movie.year = movie_info.release_date[:4] if hasattr(movie_info, 'release_date') and movie_info.release_date else None
                movie.runtime = getattr(movie_info, 'runtime', None)
                movie.popularity = getattr(movie_info, 'popularity', 0)
                movie.vote_count = getattr(movie_info, 'vote_count', 0)

                # Update poster and backdrop URLs
                if hasattr(movie_info, 'poster_path') and movie_info.poster_path:
                    movie.poster_url = f"https://image.tmdb.org/t/p/original{movie_info.poster_path}"
                    movie.poster_preview_url = f"https://image.tmdb.org/t/p/w500{movie_info.poster_path}"
                if hasattr(movie_info, 'backdrop_path') and movie_info.backdrop_path:
                    movie.backdrop_url = f"https://image.tmdb.org/t/p/original{movie_info.backdrop_path}"

                # Update genres
                for genre_data in movie_info.get('genres', []):
                    genre, _ = Genre.objects.get_or_create(
                        tmdb_id=genre_data['id'],
                        defaults={'name': genre_data['name']}
                    )
                    movie.genres.add(genre)

                movie.save()

                # If there's a collection, fetch its details
                if movie_info.get('belongs_to_collection'):
                    # add collection
                    collection_data = TMDBCollection().details(movie_info.belongs_to_collection['id'])
                    collection_object, created = Collection.objects.get_or_create(
                        tmdb_id=collection_data.id,
                        defaults={
                            'name': collection_data.name,
                            'overview': collection_data.overview,
                            'poster_url': f"https://image.tmdb.org/t/p/original{collection_data.poster_path}" if collection_data.poster_path else None,
                            'backdrop_url': f"https://image.tmdb.org/t/p/original{collection_data.backdrop_path}" if collection_data.backdrop_path else None,
                        }
                    )
                    for movie_item in collection_data.parts:
                        if Movie.objects.filter(tmdb_id=movie_item.id).exists():
                            Movie.objects.filter(tmdb_id=movie_item.id).update(collection=collection_object)
                        else:
                            movie_details = tmdb_movie.details(movie_item.id)
                            Movie.objects.create(
                                tmdb_id=movie_details.id,
                                title=movie_details.title,
                                plot=movie_details.overview,
                                rating=movie_details.vote_average,
                                runtime=movie_details.runtime,
                                popularity=movie_details.popularity,
                                vote_count=movie_details.vote_count,
                                year=movie_details.release_date[:4] if hasattr(
                                    movie_details, 'release_date') and movie_details.release_date else None,
                                poster_url=f"https://image.tmdb.org/t/p/original{movie_details.poster_path}" if movie_details.poster_path else None,
                                poster_preview_url=f"https://image.tmdb.org/t/p/w500{
                                    movie_details.poster_path}" if movie_details.poster_path else None,
                                backdrop_url=f"https://image.tmdb.org/t/p/original{
                                    movie_details.backdrop_path}" if movie_details.backdrop_path else None,
                                collection=collection_object
                            )

            except Exception as e:
                return Response(
                    {'detail': f'Failed to fetch movie details: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        if not movie.cast.exists():
            credits = tmdb_movie.credits(movie.tmdb_id)
            # Update cast
            if hasattr(credits, 'cast'):
                for cast_member in credits.cast._obj_list[:10]:  # Limit to top 10 cast members
                    person, _ = Person.objects.get_or_create(
                        tmdb_id=cast_member['id'],
                        defaults={
                            'name': cast_member['name'],
                            'profile_path': f"https://image.tmdb.org/t/p/original{cast_member['profile_path']}" if cast_member.get('profile_path') else None
                        }
                    )
                    MovieCast.objects.create(movie=movie, person=person, character=cast_member.get('character', None))

            # Update directors
            if hasattr(credits, 'crew'):
                for crew_member in credits.crew:
                    if crew_member['job'] == 'Director':
                        person, _ = Person.objects.get_or_create(
                            tmdb_id=crew_member['id'],
                            defaults={
                                'name': crew_member['name'],
                                'profile_path': f"https://image.tmdb.org/t/p/original{crew_member['profile_path']}" if crew_member.get('profile_path') else None
                            }
                        )
                        movie.directors.add(person)

        serializer = self.get_serializer(movie)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MovieListsView(generics.GenericAPIView):
    serializer_class = MovieSerializer

    def get(self, request):
        # Get popular movies from TMDB and store in our DB
        tmdb_movie = TMDBMovie()
        popular_movies = tmdb_movie.popular()
        now_playing = tmdb_movie.now_playing()

        # Process and store popular movies
        print(popular_movies['results'])
        popular_stored = []
        for movie in popular_movies['results']._obj_list[:12]:  # Limit to 12 movies
            movie_obj, _ = Movie.objects.get_or_create(
                tmdb_id=movie.id,
                defaults={
                    'title': movie.title,
                    'plot': movie.overview,
                    'rating': movie.vote_average,
                    'poster_url': f"https://image.tmdb.org/t/p/original{movie.poster_path}" if movie.poster_path else None,
                    'poster_preview_url': f"https://image.tmdb.org/t/p/w500{movie.poster_path}" if movie.poster_path else None,
                    'backdrop_url': f"https://image.tmdb.org/t/p/original{movie.backdrop_path}" if movie.backdrop_path else None,
                    'year': movie.release_date[:4] if hasattr(movie, 'release_date') and movie.release_date else None,
                    'popularity': getattr(movie, 'popularity', 0),
                    'vote_count': getattr(movie, 'vote_count', 0),
                }
            )
            popular_stored.append(movie_obj)

        # Process and store now playing movies
        now_playing_stored = []
        for movie in now_playing['results']._obj_list[:12]:
            movie_obj, _ = Movie.objects.get_or_create(
                tmdb_id=movie.id,
                defaults={
                    'title': movie.title,
                    'plot': movie.overview,
                    'rating': movie.vote_average,
                    'poster_url': f"https://image.tmdb.org/t/p/original{movie.poster_path}" if movie.poster_path else None,
                    'poster_preview_url': f"https://image.tmdb.org/t/p/w500{movie.poster_path}" if movie.poster_path else None,
                    'backdrop_url': f"https://image.tmdb.org/t/p/original{movie.backdrop_path}" if movie.backdrop_path else None,
                    'year': movie.release_date[:4] if hasattr(movie, 'release_date') and movie.release_date else None,
                    'popularity': getattr(movie, 'popularity', 0),
                    'vote_count': getattr(movie, 'vote_count', 0),
                }
            )
            now_playing_stored.append(movie_obj)

        # Get top rated movies from our database
        top_rated = Movie.objects.filter(
            rating__gt=0,
            vote_count__gt=1000
        ).order_by('-rating')[:12]

        response_data = {
            'popular': self.get_serializer(popular_stored, many=True).data,
            'now_playing': self.get_serializer(now_playing_stored, many=True).data,
            'top_rated': self.get_serializer(top_rated, many=True).data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


# Add this new view to handle movie lists
class MovieListView(generics.ListAPIView):
    serializer_class = WatchlistMoviesSerializer

    def get_queryset(self):
        list_type = self.kwargs.get('list_type')
        user = self.request.user

        if not user.is_authenticated:
            return []

        watchlist_items = Watchlist.objects.filter(user=user)

        if list_type == 'recently_watched':
            return watchlist_items.filter(
                status=Watchlist.Statuses.WATCHED
            ).order_by('-updated_at')
        elif list_type == 'want_to_watch':
            return watchlist_items.filter(
                status=Watchlist.Statuses.WATCHLIST
            ).order_by('-created_at')
        elif list_type == 'favorites':
            return watchlist_items.filter(
                status=Watchlist.Statuses.FAVORITE
            ).order_by('-created_at')

        return []
