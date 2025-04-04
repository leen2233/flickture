"""
TMDB API client utility for handling all TMDB API interactions.
"""
import requests
from typing import List, Dict, Any, Optional
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TMDBClient:
    """
    Client for interacting with The Movie Database (TMDB) API.
    Handles all API requests and response processing.
    """

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.params = {'api_key': api_key}

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a GET request to the TMDB API.

        Args:
            endpoint: API endpoint to call
            params: Optional query parameters

        Returns:
            JSON response from the API

        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        response = self.session.get(f"{self.BASE_URL}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    def _get_image_url(self, path: str, size: str = 'original') -> Optional[str]:
        """Generate full image URL from path"""
        if not path:
            return None
        return f"{self.IMAGE_BASE_URL}/{size}{path}"

    def search_movies(self, query: str, page: int = 1) -> List[Dict]:
        """
        Search for movies by title.

        Args:
            query: Search term
            page: Page number for pagination

        Returns:
            List of movie results
        """
        params = {'query': query, 'page': page}
        response = self._get('search/movie', params)
        return response.get('results', [])

    def get_movie_details(self, movie_id: int) -> Dict:
        """
        Get detailed information about a specific movie.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Movie details
        """
        return self._get(f'movie/{movie_id}')

    def get_movie_credits(self, movie_id: int) -> Dict:
        """
        Get cast and crew information for a movie.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Movie credits including cast and crew
        """
        return self._get(f'movie/{movie_id}/credits')

    def get_person_details(self, person_id: int) -> Dict:
        """
        Get detailed information about a person.

        Args:
            person_id: TMDB person ID

        Returns:
            Person details
        """
        return self._get(f'person/{person_id}')

    def get_person_credits(self, person_id: int) -> Dict:
        """
        Get movie credits for a person.

        Args:
            person_id: TMDB person ID

        Returns:
            Person's movie credits
        """
        return self._get(f'person/{person_id}/movie_credits')

    def get_popular_movies(self, page: int = 1) -> List[Dict]:
        """Get current popular movies"""
        response = self._get('movie/popular', {'page': page})
        return response.get('results', [])

    def get_now_playing_movies(self, page: int = 1) -> List[Dict]:
        """Get movies currently in theaters"""
        response = self._get('movie/now_playing', {'page': page})
        return response.get('results', [])

    def get_top_rated_movies(self, page: int = 1) -> List[Dict]:
        """Get top rated movies"""
        response = self._get('movie/top_rated', {'page': page})
        return response.get('results', [])

    def get_collection_details(self, collection_id: int) -> Dict:
        """
        Get details about a movie collection.

        Args:
            collection_id: TMDB collection ID

        Returns:
            Collection details including all movies
        """
        return self._get(f'collection/{collection_id}')

    def process_movie_data(self, movie_data: Dict) -> Dict:
        """
        Process raw movie data from TMDB API to our format.

        Args:
            movie_data: Raw movie data from TMDB

        Returns:
            Processed movie data ready for our database
        """
        return {
            'tmdb_id': movie_data['id'],
            'title': movie_data['title'],
            'plot': movie_data.get('overview'),
            'rating': movie_data.get('vote_average'),
            'year': movie_data.get('release_date', '')[:4] if movie_data.get('release_date') else None,
            'runtime': movie_data.get('runtime'),
            'popularity': movie_data.get('popularity', 0),
            'vote_count': movie_data.get('vote_count', 0),
            'poster_url': self._get_image_url(movie_data.get('poster_path')),
            'poster_preview_url': self._get_image_url(movie_data.get('poster_path'), 'w500'),
            'backdrop_url': self._get_image_url(movie_data.get('backdrop_path')),
        }

    def process_person_data(self, person_data: Dict) -> Dict:
        """
        Process raw person data from TMDB API to our format.

        Args:
            person_data: Raw person data from TMDB

        Returns:
            Processed person data ready for our database
        """
        return {
            'tmdb_id': person_data['id'],
            'name': person_data['name'],
            'profile_path': self._get_image_url(person_data.get('profile_path')),
        }

    def process_collection_data(self, collection_data: Dict) -> Dict:
        """
        Process raw collection data from TMDB API to our format.

        Args:
            collection_data: Raw collection data from TMDB

        Returns:
            Processed collection data ready for our database
        """
        return {
            'tmdb_id': collection_data['id'],
            'name': collection_data['name'],
            'overview': collection_data.get('overview'),
            'poster_url': self._get_image_url(collection_data.get('poster_path')),
            'backdrop_url': self._get_image_url(collection_data.get('backdrop_path')),
        }

    def search_multi(self, query: str, page: int = 1) -> List[Dict]:
        """
        Search for movies, TV shows, and people.

        Args:
            query: Search term
            page: Page number for pagination

        Returns:
            List of results with type indicators
        """
        logger.debug(f"Searching multi content for query: {query}")
        params = {'query': query, 'page': page}
        response = self._get('search/multi', params)
        results = response.get('results', [])

        processed_results = []
        for item in results:
            media_type = item.get('media_type')

            if media_type == 'movie':
                processed_results.append({
                    **self.process_movie_data(item),
                    'media_type': 'movie'
                })
            elif media_type == 'tv':
                processed_results.append({
                    'tmdb_id': item['id'],
                    'title': item.get('name'),
                    'original_title': item.get('original_name'),
                    'media_type': 'tv',
                    'first_air_date': item.get('first_air_date'),
                    'year': item.get('first_air_date', '')[:4] if item.get('first_air_date') else None,
                    'overview': item.get('overview'),
                    'rating': item.get('vote_average'),
                    'vote_count': item.get('vote_count'),
                    'popularity': item.get('popularity'),
                    'poster_url': self._get_image_url(item.get('poster_path')),
                    'poster_preview_url': self._get_image_url(item.get('poster_path'), 'w500'),
                    'backdrop_url': self._get_image_url(item.get('backdrop_path'))
                })
            elif media_type == 'person':
                processed_results.append({
                    **self.process_person_data(item),
                    'media_type': 'person',
                    'known_for_department': item.get('known_for_department'),
                    'known_for': [self.process_movie_data(m) for m in item.get('known_for', []) if m.get('media_type') == 'movie']
                })

        return {
            'results': processed_results,
            'total_pages': response.get('total_pages', 1),
            'total_results': response.get('total_results', 0)
        }

    def get_tv_details(self, tv_id: int) -> Dict:
        """
        Get detailed information about a specific TV show.

        Args:
            tv_id: TMDB TV show ID

        Returns:
            TV show details
        """
        return self._get(f'tv/{tv_id}')

    def get_tv_credits(self, tv_id: int) -> Dict:
        """
        Get cast and crew information for a TV show.

        Args:
            tv_id: TMDB TV show ID

        Returns:
            TV show credits including cast and crew
        """
        return self._get(f'tv/{tv_id}/credits')

    def process_tv_data(self, tv_data: Dict) -> Dict:
        """
        Process raw TV show data from TMDB API to our format.

        Args:
            tv_data: Raw TV show data from TMDB

        Returns:
            Processed TV show data ready for our database
        """
        return {
            'tmdb_id': tv_data['id'],
            'title': tv_data.get('name'),
            'original_title': tv_data.get('original_name'),
            'overview': tv_data.get('overview'),
            'first_air_date': tv_data.get('first_air_date'),
            'last_air_date': tv_data.get('last_air_date'),
            'status': tv_data.get('status'),
            'number_of_seasons': tv_data.get('number_of_seasons'),
            'number_of_episodes': tv_data.get('number_of_episodes'),
            'episode_run_time': tv_data.get('episode_run_time', []),
            'rating': tv_data.get('vote_average'),
            'popularity': tv_data.get('popularity', 0),
            'poster_path': tv_data.get('poster_path'),
            'backdrop_path': tv_data.get('backdrop_path'),
        }
