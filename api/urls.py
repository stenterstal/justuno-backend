from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameCreateAPIView, GameMinMaxView, PlayerGameResultsView, PlayerViewSet, LeaderboardAPIView

router = DefaultRouter()
router.register(r'players', PlayerViewSet, basename='player')

urlpatterns = [
    path('', include(router.urls)),
    path("games/", GameCreateAPIView.as_view(), name="game-create"),
    path('games/dates/', GameMinMaxView.as_view(), name='game-minmax'),
    path("leaderboard/", LeaderboardAPIView.as_view(), name="leaderboard"),
    path('games/<str:player_name>/', PlayerGameResultsView.as_view(), name='player-results'),]
