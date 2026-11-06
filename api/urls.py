from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameCreateAPIView, GameMinMaxView, LoginView, LogoutView, MeView, PlayerGameResultsView, PlayerViewSet, LeaderboardAPIView, RefreshView

router = DefaultRouter()
router.register(r'players', PlayerViewSet, basename='player')

urlpatterns = [
    path('', include(router.urls)),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/refresh/", RefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("games/", GameCreateAPIView.as_view(), name="game-create"),
    path('games/dates/', GameMinMaxView.as_view(), name='game-minmax'),
    path("leaderboard/", LeaderboardAPIView.as_view(), name="leaderboard"),
    # path converter so names containing a slash still resolve
    path('players/<path:player_name>/games/', PlayerGameResultsView.as_view(), name='player-results'),
]
