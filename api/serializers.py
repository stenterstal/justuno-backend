from rest_framework import serializers
from django.db import transaction
from .models import Player, GameResult, Game


class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['name', 'uuid']


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
        fields = ("id", "played_at", "results")

    def validate_results(self, results):
        if len(results) < 2:
            raise serializers.ValidationError(
                "A game must have at least 2 players."
            )

        positions = [r["position"] for r in results]
        if len(set(positions)) != len(positions):
            raise serializers.ValidationError(
                "Positions must be unique per game."
            )

        if min(positions) != 1:
            raise serializers.ValidationError(
                "Positions must start at 1."
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
    ranking = serializers.IntegerField()
    games_played = serializers.IntegerField()
    games_won = serializers.IntegerField()
    average_score = serializers.FloatField()
    final_score = serializers.FloatField()