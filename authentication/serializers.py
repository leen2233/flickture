from rest_framework import serializers

from core.models import Favorite, Watchlist
from core.serializers import MovieSerializer

from .models import User


class CaptchaSerializer(serializers.Serializer):
    captcha_key = serializers.CharField(read_only=True)
    captcha_image = serializers.CharField(read_only=True)


class SignUpSerializer(serializers.ModelSerializer):
    captcha_key = serializers.CharField()
    captcha_input = serializers.CharField()

    class Meta:
        model = User
        fields = ["username", "email", "password", "full_name", "captcha_key", "captcha_input"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        validated_data.pop("captcha_key")
        validated_data.pop("captcha_input")
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    recently_watched = serializers.SerializerMethodField()
    watchlist = serializers.SerializerMethodField()
    watchlist_count = serializers.SerializerMethodField()
    favorites = serializers.SerializerMethodField()
    favorites_count = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    movies_watched = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "username",
            "full_name",
            "email",
            "about",
            "avatar",
            "banner_image",
            "follower_count",
            "following_count",
            "is_following",
            "is_public",
            "movies_watched",
            "recently_watched",
            "watchlist",
            "watchlist_count",
            "favorites",
            "favorites_count",
        ]
        read_only_fields = ["follower_count", "following_count", "is_following"]

    def get_follower_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def get_is_following(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user in obj.followers.all()
        return False

    def get_movies_watched(self, obj):
        return Watchlist.objects.filter(user=obj, status=Watchlist.Statuses.WATCHED).count()

    def get_recently_watched(self, obj):
        watchlist = Watchlist.objects.filter(user=obj, status=Watchlist.Statuses.WATCHED).order_by("-created_at")[:5]
        return [{"movie": MovieSerializer(item.movie).data, "updated_at": item.created_at} for item in watchlist]

    def get_watchlist(self, obj):
        watchlist = Watchlist.objects.filter(user=obj, status=Watchlist.Statuses.WATCHLIST).order_by("-created_at")[:5]
        return [{"movie": MovieSerializer(item.movie).data, "updated_at": item.created_at} for item in watchlist]

    def get_watchlist_count(self, obj):
        return Watchlist.objects.filter(user=obj, status=Watchlist.Statuses.WATCHLIST).count()

    def get_favorites(self, obj):
        favorites = Favorite.objects.filter(user=obj).order_by("-created_at")[:5]
        return [{"movie": MovieSerializer(item.movie).data, "updated_at": item.created_at} for item in favorites]

    def get_favorites_count(self, obj):
        return Favorite.objects.filter(user=obj).count()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Serializer for displaying minimal user information in lists"""

    class Meta:
        model = User
        fields = ["username", "full_name", "avatar"]
        read_only_fields = fields


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["is_public"]


class WatchlistItemSerializer(serializers.ModelSerializer):
    """Serializer for user's watchlist items with movie details and favorite status"""
    movie = MovieSerializer(read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Watchlist
        fields = ['id', 'movie', 'status', 'created_at', 'updated_at', 'is_favorite']
        read_only_fields = fields

    def get_is_favorite(self, obj):
        """Check if the movie is in user's favorites"""
        return Favorite.objects.filter(user=obj.user, movie=obj.movie).exists()
