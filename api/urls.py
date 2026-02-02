from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameCreateAPIView, PlayerViewSet, LeaderboardAPIView

router = DefaultRouter()
router.register(r'players', PlayerViewSet, basename='player')

urlpatterns = [
    path('', include(router.urls)),
    path("games/", GameCreateAPIView.as_view(), name="game-create"),
    path("leaderboard/", LeaderboardAPIView.as_view(), name="leaderboard"),
]
