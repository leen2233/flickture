from rest_framework import serializers
from .models import Movie, Genre, Person


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
    directors = PersonSerializer(many=True)

    class Meta:
        model = Movie
        fields = '__all__'
