from django.contrib import admin

from core.models import Collection, Comment, Genre, List, Movie, Person, Watchlist


class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "tmdb_id", "year", "popularity", "vote_count")
    search_fields = ("title", "tmdb_id")
    list_filter = ("year", "popularity", "vote_count")


# Register your models here.
admin.site.register(Movie, MovieAdmin)
admin.site.register(Person)
admin.site.register(Genre)
admin.site.register(Watchlist)
admin.site.register(Collection)
admin.site.register(Comment)
admin.site.register(List)
