from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=255)
    imdb_id = models.CharField(max_length=20, unique=True)
    headshot = models.URLField(blank=True, null=True)

    objects = models.Manager()

    def __str__(self):
        return self.name


class Filmography(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='filmography')
    movie = models.ForeignKey('Movie', on_delete=models.CASCADE)
    role = models.CharField(max_length=100, blank=True, null=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.person.name} in {self.movie.title}"


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
