from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from utils.tmdb import TMDBClient

from .models import Comment, Genre, Movie, Person, Watchlist

User = get_user_model()


class MovieModelTests(TestCase):
    """Test cases for Movie model"""

    def setUp(self):
        self.genre = Genre.objects.create(tmdb_id=1, name='Action')
        self.director = Person.objects.create(
            tmdb_id=1,
            name='Director Name',
            profile_path='http://example.com/profile.jpg'
        )
        self.movie = Movie.objects.create(
            tmdb_id=1,
            title='Test Movie',
            plot='Test plot',
            rating=8.5,
            year=2024
        )
        self.movie.genres.add(self.genre)
        self.movie.directors.add(self.director)

    def test_movie_creation(self):
        """Test creating a movie with relationships"""
        self.assertEqual(self.movie.title, 'Test Movie')
        self.assertEqual(self.movie.genres.first(), self.genre)
        self.assertEqual(self.movie.directors.first(), self.director)

    def test_movie_str_method(self):
        """Test string representation of Movie"""
        self.assertEqual(str(self.movie), 'Test Movie')

    def test_get_cast_preview(self):
        """Test getting cast preview"""
        actor = Person.objects.create(tmdb_id=2, name='Actor Name')
        self.movie.cast.create(person=actor, character='Character Name')
        self.assertEqual(len(self.movie.get_cast_preview()), 1)


class TMDBClientTests(TestCase):
    """Test cases for TMDB API client"""

    def setUp(self):
        self.client = TMDBClient(api_key='test_key')

    @patch('requests.Session.get')
    def test_search_movies(self, mock_get):
        """Test movie search functionality"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'results': [{'id': 1, 'title': 'Test Movie'}]
        }
        mock_get.return_value = mock_response
        results = self.client.search_movies('test')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Test Movie')

    @patch('requests.Session.get')
    def test_get_movie_details(self, mock_get):
        """Test fetching movie details"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 1,
            'title': 'Test Movie',
            'overview': 'Test plot'
        }
        mock_get.return_value = mock_response
        result = self.client.get_movie_details(1)
        self.assertEqual(result['title'], 'Test Movie')


class MovieAPITests(APITestCase):
    """Test cases for movie-related API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email="testuser@test.com",
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.movie = Movie.objects.create(
            tmdb_id=1,
            title='Test Movie',
            rating=8.5,
            plot='Test plot'
        )

    @patch('utils.tmdb.TMDBClient.search_multi')
    def test_movie_search_widely(self, mock_search):
        """Test wide movie search endpoint"""
        mock_search.return_value = [{
            'id': 2,
            'title': 'New Movie',
            'overview': 'Test plot',
            'vote_average': 7.5
        }]
        url = reverse('movie-search-multi')
        self.client.get(url, {'query': 'New'})
        self.assertTrue(mock_search.called)


class WatchlistTests(APITestCase):
    """Test cases for watchlist functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email="testuser@test.com",
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.movie = Movie.objects.create(
            tmdb_id=1,
            title='Test Movie',
            type=Movie.Type.movie
        )
        self.watchlist = Watchlist.objects.create(
            user=self.user,
            movie=self.movie,
            status=Watchlist.Statuses.WATCHLIST
        )

    def test_add_to_watchlist(self):
        """Test adding movie to watchlist"""
        movie2 = Movie.objects.create(tmdb_id=2, title='Another Movie', type=Movie.Type.movie)
        url = reverse('watchlist-detail', kwargs={'type': movie2.type, 'tmdb_id': str(movie2.tmdb_id)})
        data = {'status': Watchlist.Statuses.WATCHLIST, 'type': movie2.type, 'tmdb_id': str(movie2.tmdb_id)}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Watchlist.objects.filter(user=self.user, movie=movie2).exists()
        )

    def test_update_watchlist_status(self):
        """Test updating watchlist status"""
        url = reverse('watchlist-detail', kwargs={'type': self.movie.type, 'tmdb_id': str(self.movie.tmdb_id)})
        data = {'status': Watchlist.Statuses.WATCHED}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.watchlist.refresh_from_db()
        self.assertEqual(self.watchlist.status, Watchlist.Statuses.WATCHED)


class CommentTests(APITestCase):
    """Test cases for movie comments"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email="testuser@test.com",
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.movie = Movie.objects.create(
            tmdb_id=1,
            title='Test Movie',
            type=Movie.Type.movie
        )
        self.comment = Comment.objects.create(
            user=self.user,
            movie=self.movie,
            content='Test comment',
            rating=5
        )

    def test_create_comment(self):
        """Test creating a movie comment"""
        url = reverse('movie-comments-list', kwargs={'movie_id': self.movie.id, 'type': self.movie.type})
        data = {
            'movie': self.movie.id,
            'content': 'New comment',
            'rating': 4
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 2)

    def test_like_comment(self):
        """Test liking a comment"""
        url = reverse('movie-comments-like', kwargs={
            'movie_id': self.movie.id,
            'type': self.movie.type,
            'pk': self.comment.id
        })
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.likes.count(), 1)

    def test_reply_to_comment(self):
        """Test replying to a comment"""
        url = reverse('movie-comments-reply', kwargs={
            'movie_id': self.movie.id,
            'type': self.movie.type,
            'pk': self.comment.id
        })
        data = {
            'movie': self.movie.id,
            'content': 'Test reply'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.comment.responses.count(), 1)
