import uuid
from django.db import models
from django.utils.timezone import make_aware
from datetime import datetime

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
    
    def skill_score_for_month(self, year, month, K=5):
        start = make_aware(datetime(year, month, 1))
        if month == 12:
            end = make_aware(datetime(year + 1, 1, 1))
        else:
            end = make_aware(datetime(year, month + 1, 1))

        results = self.game_results.filter(
            game__played_at__gte=start,
            game__played_at__lt=end
        )

        scores = [r.normalized_score for r in results]
        if not scores:
            return 0.0

        avg_score = sum(scores) / len(scores)
        reliability = len(scores) / (len(scores) + K)
        return avg_score * reliability * 100



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
        N = self.game.player_count
        if N <= 1:
            return 0.0
        return (N - self.position) / (N - 1)