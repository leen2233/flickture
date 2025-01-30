from django.contrib import admin

from core.models import Movie, Person, Genre, Watchlist

# Register your models here.
admin.site.register(Movie)
admin.site.register(Person)
admin.site.register(Genre)
admin.site.register(Watchlist)
