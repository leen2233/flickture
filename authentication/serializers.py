from rest_framework import serializers
from rest_framework.serializers import SerializerMethodField

from core.models import Watchlist
from .models import User


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate(self, attrs):
        if not attrs.get('email'):
            raise serializers.ValidationError("Email must be provided.")
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    recently_watched = SerializerMethodField()
    watchlist = SerializerMethodField()
    favorites = SerializerMethodField()
    stats = SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'full_name',
            'about',
            'avatar',
            'banner_image',
            'recently_watched',
            'watchlist',
            'favorites',
            'stats'
        ]

    def validate_username(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def get_stats(self, obj):
        return {
            'movies_watched': Watchlist.objects.filter(user=obj, status=Watchlist.Statuses.WATCHED).count(),
            'following': obj.following.count(),
            'followers': obj.followers.count()
        }

    def get_recently_watched(self, obj):
        watchlist = Watchlist.objects.filter(
            user=obj,
            status=Watchlist.Statuses.WATCHED
        ).order_by('-created_at')[:5]
        from core.serializers import MovieSerializer
        return [{
            'movie': MovieSerializer(item.movie).data,
            'updated_at': item.created_at
        } for item in watchlist]

    def get_watchlist(self, obj):
        watchlist = Watchlist.objects.filter(
            user=obj,
            status=Watchlist.Statuses.WATCHLIST
        ).order_by('-created_at')[:5]
        from core.serializers import MovieSerializer
        return [{
            'movie': MovieSerializer(item.movie).data,
            'updated_at': item.created_at
        } for item in watchlist]

    def get_favorites(self, obj):
        watchlist = Watchlist.objects.filter(
            user=obj,
            status=Watchlist.Statuses.FAVORITE
        ).order_by('-created_at')[:5]
        from core.serializers import MovieSerializer
        return [{
            'movie': MovieSerializer(item.movie).data,
            'updated_at': item.created_at
        } for item in watchlist]
