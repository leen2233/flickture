"""
TMDB API client utility for handling all TMDB API interactions.
"""

import logging
import pprint
from datetime import datetime
from typing import Dict, List, Optional

from django.core.cache import cache

import requests

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

    def _get(self, endpoint: str, params: Dict = {}) -> Dict:
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
        print(f"Making GET request to {self.BASE_URL}/{endpoint}")
        params["api_key"] = self.api_key
        print(f"Making GET request to {self.BASE_URL}/{endpoint} with params: {params}")

        response = self.session.get(f"{self.BASE_URL}/{endpoint}", params=params)
        print(f"Received response with status code {response.status_code}")
        response.raise_for_status()
        return response.json()

    def _get_image_url(self, path: str, size: str = "original") -> Optional[str]:
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
        params = {"query": query, "page": page}
        response = self._get("search/movie", params)
        return response.get("results", [])

    def get_movie_details(self, movie_id: int) -> Dict:
        """
        Get detailed information about a specific movie.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Movie details
        """
        response = self._get(f"movie/{movie_id}")
        response = self.process_movie_data(response)
        return response

    def get_movie_credits(self, movie_id: int) -> Dict:
        """
        Get cast and crew information for a movie.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Movie credits including cast and crew
        """
        return self._get(f"movie/{movie_id}/credits")

    def get_person_details(self, person_id: int) -> Dict:
        """
        Get detailed information about a person.

        Args:
            person_id: TMDB person ID

        Returns:
            Person details
        """
        return self._get(f"person/{person_id}")

    def get_person_credits(self, person_id: int) -> Dict:
        """
        Get movie credits for a person.

        Args:
            person_id: TMDB person ID

        Returns:
            Person's movie credits
        """
        response = self._get(f"person/{person_id}/movie_credits")
        cast_response = response.get("cast", [])
        crew_response = response.get("crew", [])
        processed_cast = []
        processed_crew = []

        for movie in cast_response:
            processed_cast.append(self.process_movie_data(movie))
        for movie in crew_response:
            processed_crew.append(self.process_movie_data(movie))

        return {"cast": processed_cast, "crew": processed_crew}

    def get_popular_movies(self, page: int = 1) -> List[Dict]:
        """Get current popular movies"""
        response = self._get("movie/popular", {"page": page})
        results = response.get("results", [])
        processed_results = []
        for movie in results:
            processed_results.append(self.process_movie_data(movie))
        return processed_results

    def get_now_playing_movies(self, page: int = 1) -> List[Dict]:
        """Get movies currently in theaters"""
        response = self._get("movie/now_playing", {"page": page})
        results = response.get("results", [])
        processed_results = []
        for movie in results:
            processed_results.append(self.process_movie_data(movie))
        return processed_results

    def get_top_rated_movies(self, page: int = 1) -> List[Dict]:
        """Get top rated movies"""
        response = self._get("movie/top_rated", {"page": page})
        results = response.get("results", [])
        processed_results = []
        for movie in results:
            processed_results.append(self.process_movie_data(movie))
        return processed_results

    def get_collection_details(self, collection_id: int) -> Dict:
        """
        Get details about a movie collection.

        Args:
            collection_id: TMDB collection ID

        Returns:
            Collection details including all movies
        """
        response = self._get(f"collection/{collection_id}")
        response = self.process_collection_data(response)
        return response

    def process_movie_data(self, movie_data: Dict) -> Dict:
        """
        Process raw movie data from TMDB API to our format.

        Args:
            movie_data: Raw movie data from TMDB

        Returns:
            Processed movie data ready for our database
        """

        return {
            "tmdb_id": movie_data["id"],
            "title": movie_data["title"],
            "plot": movie_data.get("overview"),
            "rating": movie_data.get("vote_average"),
            "year": movie_data.get("release_date", "")[:4] if movie_data.get("release_date") else None,
            "runtime": movie_data.get("runtime"),
            "popularity": movie_data.get("popularity", 0),
            "vote_count": movie_data.get("vote_count", 0),
            "poster_url": self._get_image_url(movie_data.get("poster_path", "")),
            "poster_preview_url": self._get_image_url(movie_data.get("poster_path", ""), "w500"),
            "backdrop_url": self._get_image_url(movie_data.get("backdrop_path", "")),
            "genres": movie_data.get("genres", []),
            "belongs_to_collection": movie_data.get("belongs_to_collection", None),
            "type": "movie",
        }

    def process_tv_data(self, tv_data: Dict) -> Dict:
        """
        Process raw TV show data from TMDB API to our format.

        Args:
            tv_data: Raw TV show data from TMDB

        Returns:
            Processed TV show data ready for our database
        """

        return {
            "tmdb_id": tv_data["id"],
            "title": tv_data.get("name"),
            "original_title": tv_data.get("original_name"),
            "overview": tv_data.get("overview"),
            "year": tv_data.get("first_air_date", "")[:4] if tv_data.get("first_air_date") else None,
            "status": tv_data.get("status"),
            "number_of_seasons": tv_data.get("number_of_seasons"),
            "number_of_episodes": tv_data.get("number_of_episodes"),
            "episode_run_time": tv_data.get("episode_run_time", []),
            "rating": tv_data.get("vote_average"),
            "popularity": tv_data.get("popularity", 0),
            "vote_count": tv_data.get("vote_count", 0),
            "poster_url": self._get_image_url(tv_data.get("poster_path", "")),
            "poster_preview_url": self._get_image_url(tv_data.get("poster_path", ""), "w500"),
            "backdrop_url": self._get_image_url(tv_data.get("backdrop_path", "")),
            "genres": tv_data.get("genres", []),
            "season_number": tv_data.get("number_of_seasons"),
            "episode_number": tv_data.get("number_of_episodes"),
            "type": "tv",
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
            "tmdb_id": person_data["id"],
            "name": person_data["name"],
            "profile_path": self._get_image_url(person_data.get("profile_path")),
        }

    def process_collection_data(self, collection_data: Dict) -> Dict:
        """
        Process raw collection data from TMDB API to our format.

        Args:
            collection_data: Raw collection data from TMDB

        Returns:
            Processed collection data ready for our database
        """
        parts = []
        for part in collection_data["parts"]:
            parts.append(self.process_movie_data(part))

        return {
            "tmdb_id": collection_data["id"],
            "name": collection_data["name"],
            "overview": collection_data.get("overview"),
            "poster_url": self._get_image_url(collection_data.get("poster_path")),
            "backdrop_url": self._get_image_url(collection_data.get("backdrop_path")),
            "parts": parts,
        }

    def process_season_data(self, season_data: Dict) -> List:
        """
        Process raw season data from TMDB API to our format.

        Args:
            season_data: Raw season data from TMDB

        Returns:
            Processed season data ready for our database
        """
        episodes = list()

        for episode in season_data["episodes"]:
            episodes.append(
                {
                    "tmdb_id": episode["id"],
                    "season_number": episode["season_number"],
                    "episode_number": episode["episode_number"],
                    "name": episode["name"],
                    "overview": episode.get("overview"),
                    "still_url": self._get_image_url(episode.get("still_path")),
                    "vote_average": episode.get("vote_average"),
                    "runtime": episode.get("runtime"),
                    "air_date": datetime.strptime(episode.get("air_date"), "%Y-%m-%d").date()
                    if episode.get("air_date")
                    else None,
                }
            )
        return episodes
        # return {
        #     "tmdb_id": season_data["id"],
        #     "season_number": season_data["season_number"],
        #     "name": season_data["name"],
        #     "overview": season_data.get("overview"),
        #     "poster_url": self._get_image_url(season_data.get("poster_path")),
        # }

    def search_multi(self, query: str, page: int = 1) -> Dict:
        """
        Search for movies, TV shows, and people.

        Args:
            query: Search term
            page: Page number for pagination

        Returns:
            List of results with type indicators
        """
        logger.debug(f"Searching multi content for query: {query}")
        params = {"query": query, "page": page}
        response = self._get("search/multi", params)
        results = response.get("results", [])

        processed_results = []
        for item in results:
            media_type = item.get("media_type")

            if media_type == "movie":
                processed_results.append(self.process_movie_data(item))
            elif media_type == "tv":
                pprint.pprint(item)
                processed_results.append(self.process_tv_data(item))
            elif media_type == "person":
                processed_results.append(
                    {
                        **self.process_person_data(item),
                        "type": "person",
                        "known_for_department": item.get("known_for_department"),
                        "known_for": [
                            self.process_movie_data(m)
                            for m in item.get("known_for", [])
                            if m.get("media_type") == "movie"
                        ],
                    }
                )

        return {
            "results": processed_results,
            "total_pages": response.get("total_pages", 1),
            "total_results": response.get("total_results", 0),
        }

    def get_tv_details(self, tv_id: int) -> Dict:
        """
        Get detailed information about a specific TV show.

        Args:
            tv_id: TMDB TV show ID

        Returns:
            TV show details
        """
        response = self._get(f"tv/{tv_id}")
        response = self.process_tv_data(response)
        return response

    def get_tv_credits(self, tv_id: int) -> Dict:
        """
        Get cast and crew information for a TV show.

        Args:
            tv_id: TMDB TV show ID

        Returns:
            TV show credits including cast and crew
        """
        return self._get(f"tv/{tv_id}/credits")

    def get_tv_season_episodes(self, tv_id: int, season_number: int) -> Dict:
        """
        Get detailed information about a specific season of a TV show.

        Args:
            tv_id: TMDB TV show ID
            season_number: Season number

        Returns:
            Season details
        """
        response = self._get(f"tv/{tv_id}/season/{season_number}")
        response = self.process_season_data(response)
        return response
        
    def get_genre_movies(self, genre_id: int, page: int = 1) -> List[Dict]:
        """
        Get movies by genre.

        Args:
            genre_id: TMDB genre ID
            page: Page number for pagination

        Returns:
            List of movies in the specified genre
        """
        logger.debug(f"Getting movies for genre ID: {genre_id}, page: {page}")
        params = {"with_genres": genre_id, "page": page}
        response = self._get("discover/movie", params)
        results = response.get("results", [])
        processed_results = []
        for movie in results:
            processed_results.append(self.process_movie_data(movie))
        return processed_results
        
    def get_genre_pagination_info(self, genre_id: int, page: int = 1) -> Dict:
        """
        Get pagination information for genre movies.

        Args:
            genre_id: TMDB genre ID
            page: Page number for pagination

        Returns:
            Dictionary with pagination information including total_pages and total_results
        """
        logger.debug(f"Getting pagination info for genre ID: {genre_id}, page: {page}")
        
        # Try to get from cache first
        cache_key = f"tmdb_genre_pagination_{genre_id}_page_{page}"
        cached_info = cache.get(cache_key)
        
        if cached_info:
            logger.debug(f"Retrieved pagination info for genre {genre_id}, page {page} from cache")
            return cached_info
            
        params = {"with_genres": genre_id, "page": page}
        response = self._get("discover/movie", params)
        
        pagination_info = {
            "page": response.get("page", page),
            "total_pages": response.get("total_pages", 1),
            "total_results": response.get("total_results", 0)
        }
        
        # Cache for 1 hour
        cache.set(cache_key, pagination_info, 60 * 60)
        
        return pagination_info
