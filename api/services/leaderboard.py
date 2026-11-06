import calendar

from django.conf import settings
from django.utils.timezone import localdate
from ..models import GameResult


def compute_leaderboard(start_date, end_date):
    """Leaderboard entries for games played between two dates (inclusive), best first"""
    K = getattr(settings, "UNO_LEADERBOARD_K", 5)

    results = (
        GameResult.objects
        .with_player_count()
        .select_related("player")
        .filter(
            game__played_at__date__gte=start_date,
            game__played_at__date__lte=end_date
        )
    )

    leaderboard = {}

    for r in results:
        leaderboard.setdefault(r.player.name, []).append(
            r.normalized_score
        )

    entries = []

    for player, scores in leaderboard.items():
        games_played = len(scores)
        avg_score = sum(scores) / games_played
        reliability = games_played / (games_played + K)

        entries.append({
            "player": player,
            "games_played": games_played,
            "games_won": sum(1 for score in scores if score == 1.0),
            "average_score": avg_score,
            "final_score": avg_score * reliability * 100,
        })

    # Ties are broken by name so positions are stable between requests
    entries.sort(key=lambda x: (-x["final_score"], x["player"]))

    for index, entry in enumerate(entries, start=1):
        entry["position"] = index
        entry["average_score"] = round(entry["average_score"], 3)
        entry["final_score"] = round(entry["final_score"], 1)

    return entries


def get_current_month_leaderboard_positions():
    today = localdate()
    start = today.replace(day=1)
    end = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    # Only players with games this month are ranked
    return {
        entry["player"]: entry["position"]
        for entry in compute_leaderboard(start, end)
    }


def compute_leaderboard_mutations(game, before, after):
    mutations = []

    game_player_names = game.results.values_list('player__name', flat=True)

    for player_name, new_position in after.items():
        old_position = before.get(player_name)

        if old_position == new_position and player_name not in game_player_names:
            continue

        # Players new to this month's ranking have no previous position to move from
        mutations.append({
            "player": player_name,
            "old_position": old_position,
            "new_position": new_position,
            "delta": None if old_position is None else old_position - new_position,
        })

    return mutations
