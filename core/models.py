from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.cache import cache
from authentication.models import User


class PersonManager(models.Manager):
    def create_or_update_from_tmdb(self, person_data):
        """Create or update person from TMDB data"""
        person, _ = self.get_or_create(
            tmdb_id=person_data['id'],
            defaults={
                'name': person_data['name'],
                'profile_path': f"https://image.tmdb.org/t/p/original{person_data['profile_path']}" if person_data.get('profile_path') else None
            }
        )
        return person


class Person(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    profile_path = models.URLField(max_length=500, null=True, blank=True)

    objects = PersonManager()

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['tmdb_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class MovieManager(models.Manager):
    def create_or_update_from_tmdb(self, movie_data):
        """Create or update movie from TMDB data"""
        movie, created = self.get_or_create(
            tmdb_id=movie_data['id'],
            defaults={
                'title': movie_data['title'],
                'plot': movie_data.get('overview'),
                'rating': movie_data.get('vote_average'),
                'year': movie_data.get('release_date', '')[:4] if movie_data.get('release_date') else None,
                'poster_url': f"https://image.tmdb.org/t/p/original{movie_data['poster_path']}" if movie_data.get('poster_path') else None,
                'poster_preview_url': f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}" if movie_data.get('poster_path') else None,
                'backdrop_url': f"https://image.tmdb.org/t/p/original{movie_data['backdrop_path']}" if movie_data.get('backdrop_path') else None,
                'popularity': movie_data.get('popularity', 0),
                'vote_count': movie_data.get('vote_count', 0),
                'runtime': movie_data.get('runtime'),
            }
        )

        # Update genres if provided
        if movie_data.get('genres'):
            genres = []
            for genre_data in movie_data['genres']:
                genre, _ = Genre.objects.get_or_create(
                    tmdb_id=genre_data['id'],
                    defaults={'name': genre_data['name']}
                )
                genres.append(genre)
            movie.genres.set(genres)

        return movie

    def update_from_tmdb_details(self, movie, movie_data):
        """Update existing movie with detailed TMDB data"""
        movie.title = movie_data['title']
        movie.plot = movie_data.get('overview')
        movie.rating = movie_data.get('vote_average')
        movie.year = movie_data.get('release_date', '')[:4] if movie_data.get('release_date') else None
        movie.runtime = movie_data.get('runtime')
        movie.popularity = movie_data.get('popularity', 0)
        movie.vote_count = movie_data.get('vote_count', 0)

        if movie_data.get('poster_path'):
            movie.poster_url = f"https://image.tmdb.org/t/p/original{movie_data['poster_path']}"
            movie.poster_preview_url = f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}"
        if movie_data.get('backdrop_path'):
            movie.backdrop_url = f"https://image.tmdb.org/t/p/original{movie_data['backdrop_path']}"

        movie.save()

        # Update genres
        if movie_data.get('genres'):
            genres = []
            for genre_data in movie_data['genres']:
                genre, _ = Genre.objects.get_or_create(
                    tmdb_id=genre_data['id'],
                    defaults={'name': genre_data['name']}
                )
                genres.append(genre)
            movie.genres.set(genres)

        return movie


class Movie(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    plot = models.TextField(blank=True, null=True)
    rating = models.FloatField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    poster_url = models.URLField(max_length=500, null=True, blank=True)
    poster_preview_url = models.URLField(max_length=500, null=True, blank=True)
    backdrop_url = models.URLField(max_length=500, null=True, blank=True)
    popularity = models.FloatField(default=0)
    vote_count = models.IntegerField(default=0)
    runtime = models.IntegerField(null=True, blank=True)
    kind = models.CharField(max_length=50, blank=True, null=True)
    directors = models.ManyToManyField('Person', related_name='directed_movies')
    genres = models.ManyToManyField('Genre')
    collection = models.ForeignKey('Collection', on_delete=models.SET_NULL, null=True, blank=True, related_name='movies')

    objects = MovieManager()

    class Meta:
        ordering = ['-popularity']
        indexes = [
            models.Index(fields=['tmdb_id']),
            models.Index(fields=['title']),
            models.Index(fields=['year']),
            models.Index(fields=['popularity']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return self.title

    def get_cast_preview(self):
        """Get first 10 cast members"""
        return self.cast.all()[:10]


class MovieCastManager(models.Manager):
    def create_or_update_from_tmdb(self, movie, cast_data):
        """Create or update movie cast from TMDB data"""
        person = Person.objects.create_or_update_from_tmdb(cast_data)
        cast, _ = self.get_or_create(
            movie=movie,
            person=person,
            defaults={'character': cast_data.get('character')}
        )
        return cast


class MovieCast(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='cast')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='acted_movies')
    character = models.CharField(max_length=255, null=True, blank=True)

    objects = MovieCastManager()

    class Meta:
        ordering = ['id']
        unique_together = ['movie', 'person']

    def __str__(self):
        return f"{self.movie.title} - {self.person.name}"


class GenreManager(models.Manager):
    def create_or_update_from_tmdb(self, genre_data):
        """Create or update genre from TMDB data"""
        genre, _ = self.get_or_create(
            tmdb_id=genre_data['id'],
            defaults={'name': genre_data['name']}
        )
        return genre


class Genre(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)

    objects = GenreManager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CollectionManager(models.Manager):
    def create_or_update_from_tmdb(self, collection_data):
        """Create or update collection from TMDB data"""
        collection, _ = self.get_or_create(
            tmdb_id=collection_data['id'],
            defaults={
                'name': collection_data['name'],
                'overview': collection_data.get('overview'),
                'poster_url': f"https://image.tmdb.org/t/p/original{collection_data['poster_path']}" if collection_data.get('poster_path') else None,
                'backdrop_url': f"https://image.tmdb.org/t/p/original{collection_data['backdrop_path']}" if collection_data.get('backdrop_path') else None,
            }
        )
        return collection


class Collection(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    overview = models.TextField(null=True, blank=True)
    poster_url = models.URLField(max_length=500, null=True, blank=True)
    backdrop_url = models.URLField(max_length=500, null=True, blank=True)

    objects = CollectionManager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class WatchlistManager(models.Manager):
    def get_user_watchlist(self, user, status=None):
        """Get user's watchlist with optional status filter"""
        queryset = self.filter(user=user)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related('movie').order_by('-created_at')


class Watchlist(models.Model):
    class Statuses(models.TextChoices):
        WATCHLIST = "watchlist", "In Watchlist"
        WATCHED = "watched", "Watched"
        WATCHING = "watching", "Watching"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=12,
        choices=Statuses.choices,
        default=Statuses.WATCHLIST
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WatchlistManager()

    class Meta:
        unique_together = ('user', 'movie')
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.movie.title} ({self.status})"


class FavoriteManager(models.Manager):
    def get_user_favorites(self, user):
        """Get user's favorite movies"""
        return self.filter(user=user).select_related('movie').order_by('-created_at')


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FavoriteManager()

    class Meta:
        unique_together = ('user', 'movie')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"


class CommentManager(models.Manager):
    def get_movie_comments(self, movie_id, **filters):
        """Get comments for a movie with optional filters"""
        queryset = self.filter(
            movie_id=movie_id,
            parent__isnull=True
        ).select_related(
            'user'
        ).prefetch_related(
            'responses',
            'responses__user',
            'likes'
        )

        if filters.get('rating'):
            queryset = queryset.filter(rating=filters['rating'])

        order_by = filters.get('order_by', '-created_at')
        if order_by == 'likes':
            queryset = queryset.annotate(likes_count=models.Count('likes')).order_by('-likes_count')
        elif order_by == 'rating':
            queryset = queryset.order_by('-rating')
        else:
            queryset = queryset.order_by(order_by)

        return queryset


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='comments')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='responses')
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)

    objects = CommentManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['movie', 'parent', 'created_at']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f'Comment by {self.user.username} on {self.movie.title}'

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def responses_count(self):
        return self.responses.count()

    def clean(self):
        """Ensure rating is only set for top-level comments"""
        if self.parent and self.rating:
            raise models.ValidationError({
                'rating': 'Rating can only be set for top-level comments'
            })
