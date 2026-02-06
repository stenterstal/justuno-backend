from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response
from django.db.models import Min, Max
from django.db.models.functions import TruncMonth
from .services.leaderboard import compute_leaderboard_mutations, get_current_month_leaderboard_positions
from .models import Game, Player, GameResult
from .serializers import GameResultSerializer, PlayerSerializer, GameCreateSerializer, LeaderboardEntrySerializer
from django.conf import settings
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


@extend_schema(
    request=GameCreateSerializer,
    responses={
        201: {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "player_count": {"type": "integer"},
            },
        }
    },
)
class GameCreateAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        leaderboard_before = get_current_month_leaderboard_positions()

        serializer = GameCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game = serializer.save()

        leaderboard_after = get_current_month_leaderboard_positions()

        mutations = compute_leaderboard_mutations(
            game,
            leaderboard_before,
            leaderboard_after
        )
        
        return Response(
            {
                "player_count": game.player_count,
                "leaderboard_mutations": mutations
            },
            status=status.HTTP_201_CREATED
        )

class PlayerGameResultsView(generics.ListAPIView):
    serializer_class = GameResultSerializer

    def get_queryset(self):
        player_name = self.kwargs.get('player_name')
        try:
            player = Player.objects.get(name=player_name)
        except Player.DoesNotExist:
            raise NotFound(detail="Player not found")

        return GameResult.objects\
            .filter(player=player)\
            .select_related('game')\
            .order_by('-game__played_at')[:20]
    

class LeaderboardAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Retrieve leaderboard scores for a date range",
        description=(
            "Returns a leaderboard based on UNO games played between two dates. "
            "Scores are calculated using a normalized position score with a "
            "reliability factor."
        ),
        parameters=[
            OpenApiParameter(
                name="start",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Start date (inclusive), format YYYY-MM-DD",
                required=True,
            ),
            OpenApiParameter(
                name="end",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="End date (inclusive), format YYYY-MM-DD",
                required=True,
            ),
        ],
        responses={200: LeaderboardEntrySerializer(many=True)},
        tags=["Leaderboard"],
    )
    def get(self, request):
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")

        if not start_param or not end_param:
            raise ValidationError(
                "Query parameters 'start' and 'end' are required."
            )

        start_date = parse_date(start_param)
        end_date = parse_date(end_param)

        if not start_date or not end_date:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD.")

        K = getattr(settings, "UNO_LEADERBOARD_K", 5)

        results = (
            GameResult.objects
            .select_related("player", "game")
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

        response_data = []

        for player, scores in leaderboard.items():
            games_played = len(scores)
            games_won = sum(1 for game in scores if game == 1.0)
            avg_score = sum(scores) / games_played
            reliability = games_played / (games_played + K)
            final_score = avg_score * reliability * 100

            response_data.append({
                "player": player,
                "games_played": games_played,
                "games_won": games_won,
                "average_score": round(avg_score, 3),
                "final_score": round(final_score, 1),
            })

        response_data.sort(
            key=lambda x: x["final_score"],
            reverse=True
        )

        # Add ranking / position
        for index, entry in enumerate(response_data, start=1):
            entry["position"] = index

        return Response(response_data)

class GameMinMaxView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Truncate played_at to first day of the month
        truncated = Game.objects.annotate(month=TruncMonth('played_at'))

        # Aggregate min and max month
        min_max = truncated.aggregate(
            min=Min('month'),
            max=Max('month')
        )

        # Format as "yyyy-mm"
        def format_ym(date):
            return date.strftime('%Y-%m') if date else None

        return Response({
            "min": format_ym(min_max['min']),
            "max": format_ym(min_max['max'])
        })