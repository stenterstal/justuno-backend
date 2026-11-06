import uuid
from django.db import models
from django.db.models import Count

# Create your models here.
class Player(models.Model):
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Game(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    played_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Game {self.id} ({self.played_at.date()})"

    @property
    def player_count(self):
        return self.results.count()
    


class GameResultQuerySet(models.QuerySet):
    def with_player_count(self):
        # Avoids a COUNT query per result when computing normalized scores
        return self.select_related("game").annotate(game_player_count=Count("game__results"))


class GameResult(models.Model):
    game = models.ForeignKey(
        Game,
        related_name="results",
        on_delete=models.CASCADE
    )
    player = models.ForeignKey(
        Player,
        related_name="game_results",
        on_delete=models.CASCADE
    )
    position = models.PositiveIntegerField()

    objects = GameResultQuerySet.as_manager()

    class Meta:
        unique_together = ("game", "player")
        ordering = ["position"]

    def __str__(self):
        return f"{self.player} - pos {self.position} in {self.game}"

    @property
    def normalized_score(self):
        """
        (N - p) / (N - 1)
        """
        N = getattr(self, "game_player_count", None)
        if N is None:
            N = self.game.player_count
        if N <= 1:
            return 0.0
        return (N - self.position) / (N - 1)