from django.db import models

from authentication.models import User


class Person(models.Model):
    name = models.CharField(max_length=255)
    imdb_id = models.CharField(max_length=20, unique=True)
    headshot = models.URLField(blank=True, null=True)

    objects = models.Manager()

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=255)
    imdb_id = models.CharField(max_length=20, unique=True)
    plot = models.TextField(blank=True, null=True)
    rating = models.FloatField(default=0)
    year = models.IntegerField(blank=True, null=True)
    poster_url = models.URLField(blank=True, null=True)
    poster_preview_url = models.URLField(blank=True, null=True)
    kind = models.CharField(max_length=50, blank=True, null=True)
    directors = models.ManyToManyField(Person, related_name='directed_movies')
    cast = models.ManyToManyField(Person, related_name='acted_movies')
    genres = models.ManyToManyField('Genre')

    objects = models.Manager()

    def __str__(self):
        return self.title


class Genre(models.Model):
    name = models.CharField(max_length=50)

    objects = models.Manager()

    def __str__(self):
        return self.name


class Watchlist(models.Model):
    class Statuses(models.TextChoices):
        NOT_WATCHED = "not_wached", "Not Watched"
        WATCHED = "watched", "watched"
        WATCHING = "watching", "Watching"
        FAVORITE = "favorite", "Favorite"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=12,
        choices=Statuses.choices,
        default=Statuses.NOT_WATCHED
    )

    created_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    class Meta:
        unique_together = ('user', 'movie')
