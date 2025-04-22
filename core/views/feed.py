from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Comment, Episode, Favorite, List, Movie, Watchlist
from core.serializers import FeedEventSerializer


class FeedView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # Get last 30 days of activity by default or use query param
        days = int(request.query_params.get("days", 30))
        time_threshold = timezone.now() - timedelta(days=days)
        following = request.query_params.get("following", False)
        following_user_ids = None
        if following:
            following_user_ids = request.user.following.values_list("id", flat=True)

        # Activity types filter
        activity_types = request.query_params.getlist("types", [])
        if not activity_types:
            activity_types = ["like", "watch", "comment", "new_episode", "list_create", "new_movie"]

        feed_events = []
        event_id = 1

        # Favorites (likes)
        if "like" in activity_types:
            if following:
                favorites = (
                    Favorite.objects.filter(created_at__gte=time_threshold, user__id__in=following_user_ids)
                    .select_related("user", "movie")
                    .prefetch_related("movie__genres")
                )
            else:
                favorites = (
                    Favorite.objects.filter(created_at__gte=time_threshold, user__is_public=True)
                    .select_related("user", "movie")
                    .prefetch_related("movie__genres")
                )

            for favorite in favorites:
                feed_events.append(
                    {
                        "id": event_id,
                        "type": "like",
                        "user": favorite.user,
                        "movie": favorite.movie,
                        "timestamp": favorite.created_at,
                    }
                )
                event_id += 1

        # Watchlist entries with status "watched"
        if "watch" in activity_types:
            if following:
                watched = (
                    Watchlist.objects.filter(
                        status=Watchlist.Statuses.WATCHED,
                        updated_at__gte=time_threshold,
                        user__id__in=following_user_ids,
                    )
                    .select_related("user", "movie")
                    .prefetch_related("movie__genres")
                )
            else:
                watched = (
                    Watchlist.objects.filter(
                        status=Watchlist.Statuses.WATCHED, updated_at__gte=time_threshold, user__is_public=True
                    )
                    .select_related("user", "movie")
                    .prefetch_related("movie__genres")
                )

            for watch in watched:
                # Get rating from comment if exists
                rating = None
                comment = Comment.objects.filter(user=watch.user, movie=watch.movie, rating__isnull=False).first()

                if comment:
                    rating = comment.rating

                feed_events.append(
                    {
                        "id": event_id,
                        "type": "watch",
                        "user": watch.user,
                        "movie": watch.movie,
                        "rating": rating,
                        "timestamp": watch.updated_at,
                    }
                )
                event_id += 1

        # Comments
        if "comment" in activity_types:
            if following:
                comments = (
                    Comment.objects.filter(
                        created_at__gte=time_threshold,
                        parent__isnull=True,  # Only top-level comments
                        user__id__in=following_user_ids,
                    )
                    .select_related("user", "movie")
                    .prefetch_related("movie__genres")
                )
            else:
                comments = (
                    Comment.objects.filter(
                        created_at__gte=time_threshold,
                        parent__isnull=True,  # Only top-level comments
                        user__is_public=True,
                    )
                    .select_related("user", "movie")
                    .prefetch_related("movie__genres")
                )

            for comment in comments:
                feed_events.append(
                    {
                        "id": event_id,
                        "type": "comment",
                        "user": comment.user,
                        "movie": comment.movie,
                        "comment": comment.content,
                        "timestamp": comment.created_at,
                    }
                )
                event_id += 1

        # only show new episodes at global feed
        if not following:
            # New TV Episodes (within period)
            if "new_episode" in activity_types:
                episodes = (
                    Episode.objects.filter(air_date__gte=time_threshold)
                    .select_related("movie")
                    .prefetch_related("movie__genres")
                )

                for episode in episodes:
                    if episode.movie.type == Movie.Type.tv:
                        feed_events.append(
                            {
                                "id": event_id,
                                "type": "new_episode",
                                "movie": episode.movie,  # The TV show
                                "episode": episode,
                                "timestamp": timezone.make_aware(
                                    timezone.datetime.combine(episode.air_date, timezone.datetime.min.time())
                                ),
                            }
                        )
                        event_id += 1

        # New Lists
        if "list_create" in activity_types:
            if following:
                movie_lists = (
                    List.objects.filter(created_at__gte=time_threshold, creator__id__in=following_user_ids)
                    .select_related("creator")
                    .prefetch_related("movies")
                )
            else:
                movie_lists = (
                    List.objects.filter(created_at__gte=time_threshold, creator__is_public=True)
                    .select_related("creator")
                    .prefetch_related("movies")
                )

            for movie_list in movie_lists:
                feed_events.append(
                    {
                        "id": event_id,
                        "type": "list_create",
                        "user": movie_list.creator,
                        "list": movie_list,
                        "timestamp": movie_list.created_at,
                    }
                )
                event_id += 1

        # # New Movies added to the system
        # if "new_movie" in activity_types:
        #     # This would depend on implementation, but we're assuming new movies are those added recently
        #     # In a real system, you might tag movies as "new releases" or track when they were added to your database
        #     new_movies = Movie.objects.filter(
        #         type=Movie.Type.movie,  # Only actual movies, not TV shows
        #     ).order_by("-id")[:20]  # Get the 20 most recently added movies by ID

        #     for movie in new_movies:
        #         feed_events.append(
        #             {
        #                 "id": event_id,
        #                 "type": "new_movie",
        #                 "movie": movie,
        #                 "timestamp": timezone.now() - timedelta(days=1),  # Placeholder timestamp
        #             }
        #         )
        #         event_id += 1

        # Sort by timestamp, newest first
        feed_events.sort(key=lambda x: x["timestamp"], reverse=True)

        # Limit results and paginate if needed
        page_size = int(request.query_params.get("page_size", 20))
        page = int(request.query_params.get("page", 1))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        paginated_events = feed_events[start_idx:end_idx]

        # Serialize the feed events
        serializer = FeedEventSerializer(paginated_events, many=True, context={"request": request})

        return Response(
            {
                "results": serializer.data,
                "count": len(feed_events),
                "next": page + 1 if end_idx < len(feed_events) else None,
                "previous": page - 1 if page > 1 else None,
            }
        )
