from rest_framework import serializers

from authentication.models import User
from .models import Movie, Genre, MovieCast, Person, Watchlist, Collection, Favorite, Comment


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
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = [
            "id",
            "tmdb_id",
            "title",
            "year",
            "plot",
            "rating",
            "poster_url",
            "poster_preview_url",
            "backdrop_url",
            "popularity",
            "vote_count",
            "genres",
            "is_favorite",
        ]

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user,
                movie=obj
            ).exists()
        return False


class MovieCastSerializer(serializers.ModelSerializer):
    person = PersonSerializer()

    class Meta:
        model = MovieCast
        fields = ['person', 'character']


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'tmdb_id', 'name', 'overview', 'poster_url', 'backdrop_url']


class MovieDetailSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True)
    directors = PersonSerializer(many=True)
    cast_preview = serializers.SerializerMethodField()
    watchlist_status = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    collection = CollectionSerializer()
    collection_movies = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = [
            "id",
            "tmdb_id",
            "title",
            "year",
            "plot",
            "rating",
            "runtime",
            "poster_url",
            "poster_preview_url",
            "backdrop_url",
            "popularity",
            "vote_count",
            "genres",
            "directors",
            "cast_preview",
            "watchlist_status",
            "is_favorite",
            "collection",
            "collection_movies",
        ]

    def get_cast_preview(self, obj):
        return MovieCastSerializer(obj.cast.all()[:10], many=True).data

    def get_watchlist_status(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                watchlist_item = Watchlist.objects.get(
                    user=request.user,
                    movie=obj
                )
                return watchlist_item.status
            except Watchlist.DoesNotExist:
                return None
        return None

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user,
                movie=obj
            ).exists()
        return False

    def get_collection_movies(self, obj):
        if obj.collection:
            return MovieSerializer(
                obj.collection.movies.exclude(id=obj.id).order_by('-year')[:4],
                many=True
            ).data
        return None


class WatchlistMoviesSerializer(serializers.ModelSerializer):
    movie = serializers.SerializerMethodField()
    watchlist_status = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Watchlist
        fields = ['id', 'status', 'created_at', 'updated_at', 'movie', 'watchlist_status', 'is_favorite']

    def get_watchlist_status(self, obj):
        return obj.status

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user,
                movie=obj.movie
            ).exists()
        return False

    def get_movie(self, obj):
        return MovieSerializer(obj.movie, context=self.context).data


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


class CommentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar']


class CommentResponseSerializer(serializers.ModelSerializer):
    user = CommentUserSerializer()
    date = serializers.DateTimeField(source='created_at', format='%Y-%m-%d')

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'date']


class CommentSerializer(serializers.ModelSerializer):
    user = CommentUserSerializer()
    responses = CommentResponseSerializer(many=True)
    date = serializers.DateTimeField(source='created_at', format='%Y-%m-%d')
    likes = serializers.IntegerField(source='likes_count')
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'rating', 'content', 'date', 'likes', 'is_liked', 'responses']

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False


class CommentCreateSerializer(serializers.ModelSerializer):
    rating = serializers.IntegerField(required=False)

    class Meta:
        model = Comment
        fields = ['movie', 'rating', 'content', 'parent']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
