from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator

from authentication.models import User
from .models import Movie, Genre, MovieCast, Person, Watchlist, Collection, Favorite, Comment


class BaseSerializer(serializers.ModelSerializer):
    """Base serializer with common functionality"""
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    updated_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'tmdb_id', 'name']


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ['id', 'tmdb_id', 'name', 'profile_path']


class MovieListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for movie lists"""
    genres = GenreSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = [
            "id",
            "tmdb_id",
            "title",
            "year",
            "rating",
            "poster_preview_url",
            "genres",
            "is_favorite",
        ]

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, movie=obj).exists()
        return False


class MovieSerializer(MovieListSerializer):
    """Full movie serializer with additional fields"""
    class Meta(MovieListSerializer.Meta):
        fields = MovieListSerializer.Meta.fields + [
            "plot",
            "poster_url",
            "backdrop_url",
            "popularity",
            "vote_count",
        ]


class MovieCastSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)

    class Meta:
        model = MovieCast
        fields = ['person', 'character']


class CollectionSerializer(serializers.ModelSerializer):
    movies_count = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = ['id', 'tmdb_id', 'name', 'overview', 'poster_url', 'backdrop_url', 'movies_count']

    def get_movies_count(self, obj):
        return obj.movies.count()


class MovieDetailSerializer(MovieSerializer):
    directors = PersonSerializer(many=True, read_only=True)
    cast = MovieCastSerializer(source='cast_preview', many=True, read_only=True)
    watchlist_status = serializers.SerializerMethodField()
    collection = CollectionSerializer(read_only=True)
    collection_preview = serializers.SerializerMethodField()

    class Meta(MovieSerializer.Meta):
        fields = MovieSerializer.Meta.fields + [
            "runtime",
            "directors",
            "cast",
            "watchlist_status",
            "collection",
            "collection_preview",
        ]

    def get_cast_preview(self, obj):
        cast = obj.cast.all()[:10]
        return MovieCastSerializer(cast, many=True).data

    def get_watchlist_status(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                watchlist_item = Watchlist.objects.get(user=request.user, movie=obj)
                return watchlist_item.status
            except Watchlist.DoesNotExist:
                return None
        return None

    def get_collection_preview(self, obj):
        if obj.collection:
            preview_movies = obj.collection.movies.exclude(id=obj.id).order_by('-year')[:4]
            return MovieListSerializer(preview_movies, many=True, context=self.context).data
        return None


class WatchlistSerializer(BaseSerializer):
    """Serializer for managing watchlist entries"""
    movie = MovieListSerializer(read_only=True)
    tmdb_id = serializers.CharField(write_only=True)
    status = serializers.ChoiceField(choices=Watchlist.Statuses.choices)

    class Meta:
        model = Watchlist
        fields = ['id', 'movie', 'status', 'tmdb_id', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_tmdb_id(self, value):
        try:
            self.movie = Movie.objects.get(tmdb_id=value)
            return value
        except Movie.DoesNotExist:
            raise serializers.ValidationError("Movie with this TMDB ID does not exist")

    def create(self, validated_data):
        tmdb_id = validated_data.pop('tmdb_id')
        movie = Movie.objects.get(tmdb_id=tmdb_id)
        return Watchlist.objects.create(movie=movie, **validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested relationships"""
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar']


class CommentSerializer(BaseSerializer):
    """Serializer for movie comments with nested responses"""
    user = UserSerializer(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    responses = serializers.SerializerMethodField()
    rating = serializers.IntegerField(
        required=False,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'movie', 'rating', 'content',
            'created_at', 'updated_at', 'likes_count',
            'is_liked', 'responses'
        ]
        read_only_fields = ['user', 'likes_count', 'created_at', 'updated_at']

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_responses(self, obj):
        responses = obj.responses.all().order_by('created_at')
        return CommentResponseSerializer(responses, many=True, context=self.context).data

    def validate(self, attrs):
        # Ensure rating is only provided for top-level comments
        if attrs.get('parent') and attrs.get('rating'):
            raise serializers.ValidationError(
                {"rating": "Rating can only be set for top-level comments"}
            )
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class CommentResponseSerializer(BaseSerializer):
    """Serializer for comment responses"""
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at']
        read_only_fields = ['user', 'created_at']
