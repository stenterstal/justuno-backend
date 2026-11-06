from rest_framework import serializers
from django.db import transaction
from .models import Player, GameResult, Game


class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['name', 'uuid']

    def validate_name(self, name):
        # The name is used as a URL path segment, where "." and ".." get resolved away
        if not name.strip("."):
            raise serializers.ValidationError("Name cannot consist of only dots.")
        return name

class GameSerializer(serializers.ModelSerializer):
    player_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Game
        fields = ['played_at', 'player_count']

class GameResultSerializer(serializers.ModelSerializer):
    played_at = serializers.DateTimeField(source='game.played_at', read_only=True)
    # Requires GameResult.objects.with_player_count()
    player_count = serializers.IntegerField(source='game_player_count', read_only=True)

    class Meta:
        model = GameResult
        fields = ['position', 'played_at', 'player_count']

class GameResultCreateSerializer(serializers.ModelSerializer):
    player = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Player.objects.all()
    )

    class Meta:
        model = GameResult
        fields = ("player", "position")

class GameCreateSerializer(serializers.ModelSerializer):
    results = GameResultCreateSerializer(many=True)

    class Meta:
        model = Game
        fields = ("played_at", "results")

    def validate_results(self, results):
        if len(results) < 2:
            raise serializers.ValidationError(
                "A game must have at least 2 players."
            )

        players = [r["player"] for r in results]
        if len(set(players)) != len(players):
            raise serializers.ValidationError(
                "A player can only appear once per game."
            )

        positions = sorted(r["position"] for r in results)
        if positions != list(range(1, len(results) + 1)):
            raise serializers.ValidationError(
                "Positions must run from 1 to the number of players without gaps or duplicates."
            )

        return results

    @transaction.atomic
    def create(self, validated_data):
        results_data = validated_data.pop("results")

        game = Game.objects.create(**validated_data)

        GameResult.objects.bulk_create([
            GameResult(
                game=game,
                player=result["player"],
                position=result["position"]
            )
            for result in results_data
        ])

        return game
    

class LeaderboardEntrySerializer(serializers.Serializer):
    player = serializers.CharField()
    games_played = serializers.IntegerField()
    games_won = serializers.IntegerField()
    average_score = serializers.FloatField()
    final_score = serializers.FloatField()
    position = serializers.IntegerField()
