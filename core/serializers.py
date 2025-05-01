from django.core.validators import MaxValueValidator, MinValueValidator
from rest_framework import serializers

from authentication.models import User

from .models import Collection, Comment, Episode, Favorite, Genre, List, Movie, MovieCast, Person, Watchlist


class BaseSerializer(serializers.ModelSerializer):
    """Base serializer with common functionality"""

    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "tmdb_id", "name"]


class PersonSerializer(serializers.ModelSerializer):
    profile_path = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = "__all__"

    def get_profile_path(self, obj):
        return obj.full_profile_path


class MovieListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for movie lists"""

    genres = GenreSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = ["id", "tmdb_id", "title", "year", "rating", "poster_preview_url", "genres", "is_favorite", "type"]

    def get_is_favorite(self, obj):
        request = self.context.get("request")
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
        fields = ["person", "character"]


class CollectionSerializer(serializers.ModelSerializer):
    movies_count = serializers.SerializerMethodField()
    movies = MovieListSerializer(many=True, read_only=True)

    class Meta:
        model = Collection
        fields = ["id", "tmdb_id", "name", "overview", "poster_url", "backdrop_url", "movies_count", "movies"]

    def get_movies_count(self, obj):
        return obj.movies.count()

    def get_movies(self, obj):
        movies = obj.movies.all().order_by("year")
        return MovieListSerializer(movies, many=True, context=self.context).data


class MovieDetailSerializer(MovieSerializer):
    directors = PersonSerializer(many=True, read_only=True)
    watchlist_status = serializers.SerializerMethodField()
    collection = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    cast_count = serializers.SerializerMethodField()
    cast_preview = serializers.SerializerMethodField()

    class Meta(MovieSerializer.Meta):
        fields = MovieSerializer.Meta.fields + [
            "runtime",
            "directors",
            "cast_preview",
            "watchlist_status",
            "collection",
            "comment_count",
            "cast_count",
            "season_number",
            "episode_number",
        ]

    def get_cast_count(self, obj):
        print(obj.cast.all())
        return obj.cast.count()

    def get_cast_preview(self, obj):
        cast = obj.cast.all()[:10]
        return MovieCastSerializer(cast, many=True).data

    def get_watchlist_status(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                watchlist_item = Watchlist.objects.get(user=request.user, movie=obj)
                return watchlist_item.status
            except Watchlist.DoesNotExist:
                return None
        return None

    def get_collection(self, obj):
        if obj.collection:
            return CollectionSerializer(obj.collection, context=self.context).data
        return None

    def get_comment_count(self, obj):
        return obj.comments.count()


class WatchlistSerializer(BaseSerializer):
    """Serializer for managing watchlist entries"""

    movie = MovieListSerializer(read_only=True)
    tmdb_id = serializers.CharField(write_only=True)
    type = serializers.CharField(write_only=True)
    status = serializers.ChoiceField(choices=Watchlist.Statuses.choices)

    class Meta:
        model = Watchlist
        fields = ["id", "movie", "status", "tmdb_id", "type", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        if attrs.get("tmdb_id") or attrs.get("type"):
            try:
                print(attrs.get("tmdb_id"), attrs.get("type"))
                self.movie = Movie.objects.get(tmdb_id=attrs.get("tmdb_id"), type=attrs.get("type"))
                return attrs
            except Movie.DoesNotExist:
                raise serializers.ValidationError("Movie with this TMDB ID does not exist")
        else:
            return attrs

    def create(self, validated_data):
        tmdb_id = validated_data.pop("tmdb_id")
        type = validated_data.pop("type")
        movie = Movie.objects.get(tmdb_id=tmdb_id, type=type)
        return Watchlist.objects.create(movie=movie, **validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested relationships"""

    class Meta:
        model = User
        fields = ["id", "username", "avatar"]


class CommentSerializer(BaseSerializer):
    """Serializer for movie comments with nested responses"""

    user = UserSerializer(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    responses = serializers.SerializerMethodField()
    rating = serializers.IntegerField(required=False, validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "movie",
            "rating",
            "content",
            "created_at",
            "updated_at",
            "likes_count",
            "is_liked",
            "responses",
            "is_owner",
            "parent",
        ]
        read_only_fields = ["user", "likes_count", "created_at", "updated_at"]

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False

    def get_responses(self, obj):
        responses = obj.responses.all().order_by("created_at")
        return CommentResponseSerializer(responses, many=True, context=self.context).data

    def validate(self, attrs):
        # Ensure rating is only provided for top-level comments
        if attrs.get("parent") and attrs.get("rating"):
            raise serializers.ValidationError({"rating": "Rating can only be set for top-level comments"})
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class CommentResponseSerializer(BaseSerializer):
    """Serializer for comment responses"""

    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "user", "content", "created_at"]
        read_only_fields = ["user", "created_at"]


class ListMovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ["id", "tmdb_id", "title", "year", "poster_preview_url", "rating", "type"]


class ListSerializer(serializers.ModelSerializer):
    creator = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    movies_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = List
        fields = [
            "id",
            "name",
            "description",
            "thumbnail",
            "backdrop",
            "creator",
            "likes_count",
            "movies_count",
            "is_liked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["creator", "likes_count", "movies_count", "created_at", "updated_at"]

    def get_creator(self, obj):
        return obj.creator.username

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False


class ListDetailSerializer(ListSerializer):
    movies = ListMovieSerializer(many=True, read_only=True)

    class Meta(ListSerializer.Meta):
        fields = ListSerializer.Meta.fields + ["movies"]


class EpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episode
        fields = "__all__"


class FeedEventSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.CharField()
    user = serializers.SerializerMethodField()
    movie = serializers.SerializerMethodField()
    show = serializers.SerializerMethodField()
    episode = serializers.SerializerMethodField()
    list = serializers.SerializerMethodField()
    comment = serializers.CharField(required=False)
    rating = serializers.FloatField(required=False)
    timestamp = serializers.DateTimeField()

    def get_user(self, obj):
        if obj.get("type") == "new_movie" or obj.get("type") == "new_episode":
            return None

        user = obj.get("user")
        if not user:
            return None

        return {
            "id": user.id,
            "username": user.username,
            "name": user.full_name or user.username,
            "avatar": self.context["request"].build_absolute_uri(user.avatar.url)
            if user.avatar
            else "https://flickture.leen2233.me/default-avatar.png",
        }

    def get_movie(self, obj):
        if obj.get("type") == "new_episode" or obj.get("type") == "list_create":
            return None

        movie = obj.get("movie")
        if not movie:
            return None

        genres = GenreSerializer(movie.genres.all(), many=True).data
        genre_names = [genre["name"] for genre in genres]

        return {
            "id": movie.id,
            "tmdb_id": movie.tmdb_id,
            "title": movie.title,
            "poster": movie.poster_url,
            "year": str(movie.year) if movie.year else "",
            "genres": genre_names,
            "overview": movie.plot,
            "runtime": movie.runtime,
            "vote_count": movie.vote_count,
            "rating": movie.rating,
            "type": movie.type,
        }

    def get_show(self, obj):
        if obj.get("type") != "new_episode":
            return None

        show = obj.get("movie")
        if not show:
            return None

        genres = GenreSerializer(show.genres.all(), many=True).data
        genre_names = [genre["name"] for genre in genres]

        return {
            "id": show.id,
            "tmdb_id": show.tmdb_id,
            "title": show.title,
            "poster": show.poster_url,
            "year": str(show.year) if show.year else "",
            "genres": genre_names,
            "overview": show.plot,
            "rating": show.rating,
            "type": show.type,
        }

    def get_episode(self, obj):
        if obj.get("type") != "new_episode":
            return None

        episode = obj.get("episode")
        if not episode:
            return None

        return {"season": episode.season_number, "episode": episode.episode_number, "title": episode.name}

    def get_list(self, obj):
        if obj.get("type") != "list_create":
            return None

        movie_list = obj.get("list")
        if not movie_list:
            return None

        return {
            "id": movie_list.id,
            "title": movie_list.name,
            "description": movie_list.description,
            "thumbnail": self.context["request"].build_absolute_uri(movie_list.thumbnail.url),
            "movie_count": movie_list.movies.count(),
        }
