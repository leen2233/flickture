from rest_framework import serializers
from .models import Movie, Genre, Person, Watchlist


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = '__all__'


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = '__all__'


class MovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True)

    class Meta:
        model = Movie
        fields = ["title", "imdb_id", "year", "poster_preview_url", "kind", "genres"]


class MovieDetailSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True)
    directors = PersonSerializer(many=True)
    cast_preview = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        exclude = ["cast"]

    def get_cast_preview(self, obj):
        return PersonSerializer(obj.cast.all()[:5], many=True).data


class WatchlistSerializer(serializers.ModelSerializer):
    imdb_id = serializers.CharField(write_only=True)

    class Meta:
        model = Watchlist
        fields = ['id', 'user', 'status', 'created_at', 'imdb_id', "movie"]
        read_only_fields = ['user', "movie"]

    def create(self, validated_data):
        # Get the movie using the imdb_id
        imdb_id = validated_data.pop('imdb_id')
        movie = Movie.objects.get(imdb_id=imdb_id)

        # Create the watchlist entry with the movie
        return Watchlist.objects.create(movie=movie, **validated_data)

    def update(self, instance, validated_data):
        # Update the movie using the imdb_id, if provided
        imdb_id = validated_data.pop('imdb_id', None)
        if imdb_id:
            movie = Movie.objects.get(imdb_id=imdb_id)
            instance.movie = movie

        # Update other fields
        return super().update(instance, validated_data)