from django.db import models

# Create your models here.
class Player(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
# class Game(models.Model):
#     date_played = models.DateTimeField(auto_now_add=True)
#     players = models.ManyToManyField(
#         Player,
#         through='GameResult',
#         related_name='games'
#     )

#     def __str__(self):
#         return f"Game {self.id} on {self.date_played.strftime('%Y-%m-%d')}"

#     def get_results_ordered(self):
#         """Return players in order of their finish."""
#         return self.gameresult_set.order_by('position')
    
# class GameResult(models.Model):
#     game = models.ForeignKey(Game, on_delete=models.CASCADE)
#     player = models.ForeignKey(Player, on_delete=models.CASCADE)
#     position = models.PositiveIntegerField(help_text="1 = first place, 2 = second, etc.")

#     class Meta:
#         unique_together = ('game', 'player')
#         ordering = ['position']

#     def __str__(self):
#         return f"{self.player.name} - Game {self.game.id} - Position {self.position}"