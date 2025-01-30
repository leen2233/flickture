from django.db import models

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
        FAVORITE = "favorite", "Favorite"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=12,
        choices=Statuses.choices,
        default=Statuses.WATCHLIST
    )

    created_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    class Meta:
        unique_together = ('user', 'movie')
