from django.utils.timezone import now
from ..models import Player


def get_current_month_leaderboard_positions():
    today = now()
    year = today.year
    month = today.month

    players = Player.objects.all()

    scored_players = [
        (player.name, player.skill_score_for_month(year, month))
        for player in players
    ]

    scored_players.sort(key=lambda x: (-x[1], x[0]))

    positions = {}
    for idx, (player_name, _) in enumerate(scored_players, start=1):
        positions[player_name] = idx

    return positions


def compute_leaderboard_mutations(game, before, after):
    mutations = []

    game_player_names = game.results.values_list('player__name', flat=True)

    for player_name, new_position in after.items():
        old_position = before.get(player_name)

        if old_position is None or old_position == new_position and player_name not in game_player_names:
            continue

        mutations.append({
            "player": player_name,
            "old_position": old_position,
            "new_position": new_position,
            "delta": old_position - new_position,
        })

    return mutations