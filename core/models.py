from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from authentication.models import User


class Person(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    profile_path = models.URLField(max_length=500, null=True, blank=True)

    objects = models.Manager()

    def __str__(self):
        return self.name


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

    objects = models.Manager()

    def __str__(self):
        return self.title


class MovieCast(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='cast')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='acted_movies')
    character = models.CharField(max_length=255, null=True, blank=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.movie.title} - {self.person.name}"


class Genre(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)

    objects = models.Manager()

    def __str__(self):
        return self.name


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
    objects = models.Manager()

    class Meta:
        unique_together = ('user', 'movie')


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"


class Collection(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    overview = models.TextField(null=True, blank=True)
    poster_url = models.URLField(max_length=500, null=True, blank=True)
    backdrop_url = models.URLField(max_length=500, null=True, blank=True)

    objects = models.Manager()

    def __str__(self):
        return self.name


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='comments')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='responses')
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comment by {self.user.username} on {self.movie.title}'

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def responses_count(self):
        return self.responses.count()
