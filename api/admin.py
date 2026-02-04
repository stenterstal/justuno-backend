from django.contrib import admin
from .models import Player, Game, GameResult

admin.site.register(Player)
admin.site.register(GameResult)

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = ('id', 'played_at', 'player_count')
    
    # Make auto_now_add fields read-only in the admin detail page
    readonly_fields = ('played_at', 'player_count')