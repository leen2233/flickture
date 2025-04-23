from rest_framework import serializers

from core.models import Watchlist

from .models import User


class SignUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "password", "full_name"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
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
        ]
        read_only_fields = ["username", "follower_count", "following_count", "is_following"]

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
