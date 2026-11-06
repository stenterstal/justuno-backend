from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.timezone import localdate
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from api.models import Game, GameResult, Player

User = get_user_model()

LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"
LOGOUT_URL = "/api/auth/logout/"
ME_URL = "/api/auth/me/"
PROTECTED_URL = "/api/players/"
PLAYERS_URL = "/api/players/"
GAMES_URL = "/api/games/"
LEADERBOARD_URL = "/api/leaderboard/"


class AuthTestCase(APITestCase):
    password = "correct-horse-battery"

    def setUp(self):
        # Login throttle counts are stored in the cache
        cache.clear()
        self.user = User.objects.create_user(username="sten", password=self.password)

    def login(self, username="sten", password=None):
        return self.client.post(
            LOGIN_URL,
            {"username": username, "password": password or self.password},
            format="json",
        )

    def set_refresh_cookie(self, token):
        self.client.cookies["refresh"] = str(token)

    def assertCookiesCleared(self, response):
        for name in ("access", "refresh"):
            self.assertIn(name, response.cookies)
            self.assertEqual(response.cookies[name].value, "")


class LoginTests(AuthTestCase):
    def test_valid_credentials_set_auth_cookies(self):
        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access = response.cookies["access"]
        refresh = response.cookies["refresh"]

        self.assertTrue(access["httponly"])
        self.assertTrue(refresh["httponly"])
        self.assertEqual(access["path"], "/")
        self.assertEqual(refresh["path"], "/api/auth/")
        self.assertEqual(access["samesite"], settings.COOKIE_SAMESITE)
        self.assertEqual(refresh["samesite"], settings.COOKIE_SAMESITE)

    def test_cookie_lifetimes_match_token_lifetimes(self):
        response = self.login()

        self.assertEqual(
            int(response.cookies["access"]["max-age"]),
            settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
        )
        self.assertEqual(
            int(response.cookies["refresh"]["max-age"]),
            settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
        )

    def test_wrong_password_is_rejected(self):
        response = self.login(password="wrong")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.cookies)
        self.assertNotIn("refresh", response.cookies)

    def test_unknown_user_is_rejected(self):
        response = self.login(username="nobody")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_credentials_are_rejected(self):
        response = self.client.post(LOGIN_URL, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()

        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_is_throttled(self):
        for _ in range(5):
            self.assertEqual(
                self.login(password="wrong").status_code,
                status.HTTP_401_UNAUTHORIZED,
            )

        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertNotIn("access", response.cookies)


    def test_login_updates_last_login(self):
        self.login()

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_spoofed_forwarded_for_does_not_bypass_throttle(self):
        # nginx appends the real client IP after whatever the client sent
        for i in range(5):
            self.client.post(
                LOGIN_URL,
                {"username": "sten", "password": "wrong"},
                format="json",
                HTTP_X_FORWARDED_FOR=f"10.0.0.{i}, 203.0.113.7",
            )

        response = self.client.post(
            LOGIN_URL,
            {"username": "sten", "password": self.password},
            format="json",
            HTTP_X_FORWARDED_FOR="10.0.0.99, 203.0.113.7",
        )

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class CookieAuthenticationTests(AuthTestCase):
    def test_access_cookie_authenticates_request(self):
        self.login()

        response = self.client.get(PROTECTED_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_request_without_cookie_is_rejected(self):
        response = self.client.get(PROTECTED_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_access_token_is_rejected(self):
        self.client.cookies["access"] = "not-a-jwt"

        response = self.client.get(PROTECTED_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_access_token_is_rejected(self):
        token = AccessToken.for_user(self.user)
        token.set_exp(lifetime=-timedelta(seconds=1))
        self.client.cookies["access"] = str(token)

        response = self.client.get(PROTECTED_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_is_not_accepted_as_access_token(self):
        self.client.cookies["access"] = str(RefreshToken.for_user(self.user))

        response = self.client.get(PROTECTED_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bearer_header_is_ignored(self):
        token = AccessToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(PROTECTED_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RefreshTests(AuthTestCase):
    def test_refresh_issues_new_tokens(self):
        login = self.login()
        old_access = login.cookies["access"].value
        old_refresh = login.cookies["refresh"].value

        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.cookies["access"].value, old_access)
        self.assertNotEqual(response.cookies["refresh"].value, old_refresh)

    def test_refreshed_access_token_authenticates(self):
        self.login()
        self.client.post(REFRESH_URL)

        response = self.client.get(PROTECTED_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_old_refresh_token_cannot_be_reused(self):
        old_refresh = self.login().cookies["refresh"].value
        self.client.post(REFRESH_URL)

        self.set_refresh_cookie(old_refresh)
        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_cookie_is_rejected(self):
        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_refresh_token_is_rejected_and_cookies_cleared(self):
        self.set_refresh_cookie("not-a-jwt")

        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertCookiesCleared(response)

    def test_expired_refresh_token_is_rejected(self):
        token = RefreshToken.for_user(self.user)
        token.set_exp(lifetime=-timedelta(seconds=1))
        self.set_refresh_cookie(token)

        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_is_not_accepted_as_refresh_token(self):
        self.set_refresh_cookie(AccessToken.for_user(self.user))

        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_quoted_refresh_cookie_is_accepted(self):
        self.set_refresh_cookie(f'"{RefreshToken.for_user(self.user)}"')

        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inactive_user_cannot_refresh(self):
        self.login()
        self.user.is_active = False
        self.user.save()

        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertCookiesCleared(response)

    def test_deleted_user_cannot_refresh(self):
        self.login()
        self.user.delete()

        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertCookiesCleared(response)


class LogoutTests(AuthTestCase):
    def test_logout_clears_cookies(self):
        self.login()

        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCookiesCleared(response)

    def test_logout_revokes_refresh_token(self):
        refresh = self.login().cookies["refresh"].value
        self.client.post(LOGOUT_URL)

        self.set_refresh_cookie(refresh)
        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_cookies_succeeds(self):
        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_with_invalid_refresh_token_succeeds(self):
        self.set_refresh_cookie("not-a-jwt")

        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCookiesCleared(response)

    def test_logout_twice_succeeds(self):
        refresh = self.login().cookies["refresh"].value
        self.client.post(LOGOUT_URL)

        self.set_refresh_cookie(refresh)
        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MeTests(AuthTestCase):
    def test_me_returns_current_user(self):
        self.login()

        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"username": "sten"})

    def test_me_requires_login(self):
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class GameApiTestCase(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.login()
        for name in ("Anna", "Bram", "Cas"):
            Player.objects.create(name=name)

    def create_game(self, *results):
        return self.client.post(
            GAMES_URL,
            {"results": [{"player": p, "position": pos} for p, pos in results]},
            format="json",
        )


class GameCreateTests(GameApiTestCase):
    def test_valid_game_is_created(self):
        response = self.create_game(("Anna", 1), ("Bram", 2), ("Cas", 3))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["player_count"], 3)

    def test_position_gaps_are_rejected(self):
        response = self.create_game(("Anna", 1), ("Bram", 99))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(GameResult.objects.count(), 0)

    def test_duplicate_positions_are_rejected(self):
        response = self.create_game(("Anna", 1), ("Bram", 1))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_players_are_rejected(self):
        response = self.create_game(("Anna", 1), ("Anna", 2))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_first_game_of_month_shows_initial_ranking(self):
        response = self.create_game(("Bram", 1), ("Anna", 2))

        self.assertEqual(response.json()["leaderboard_mutations"], [
            {"player": "Bram", "old_position": None, "new_position": 1, "delta": None},
            {"player": "Anna", "old_position": None, "new_position": 2, "delta": None},
        ])

    def test_later_game_shows_movement(self):
        Player.objects.create(name="Dirk")
        # Bram 1st (100), Anna 2nd (50), Cas 3rd (0)
        self.create_game(("Bram", 1), ("Anna", 2), ("Cas", 3))

        # Averages after: Anna 0.75, Bram 0.67, Cas 0.33, Dirk 0 (new)
        response = self.create_game(("Anna", 1), ("Cas", 2), ("Bram", 3), ("Dirk", 4))

        mutations = {m["player"]: m for m in response.json()["leaderboard_mutations"]}
        self.assertEqual(
            (mutations["Anna"]["old_position"], mutations["Anna"]["new_position"], mutations["Anna"]["delta"]),
            (2, 1, 1),
        )
        self.assertEqual(
            (mutations["Bram"]["old_position"], mutations["Bram"]["new_position"], mutations["Bram"]["delta"]),
            (1, 2, -1),
        )
        self.assertEqual(mutations["Cas"]["delta"], 0)
        self.assertEqual(mutations["Dirk"]["new_position"], 4)
        self.assertIsNone(mutations["Dirk"]["old_position"])
        self.assertIsNone(mutations["Dirk"]["delta"])

    def test_only_moved_players_outside_game_are_shown(self):
        Player.objects.create(name="Dirk")
        Player.objects.create(name="Eva")
        # Anna 16.7, Bram 8.3, Cas 0
        self.create_game(("Anna", 1), ("Bram", 2), ("Cas", 3))

        # Cas rises to 14.3 and passes Bram; Anna stays first
        response = self.create_game(("Cas", 1), ("Dirk", 2))

        players = sorted(m["player"] for m in response.json()["leaderboard_mutations"])
        self.assertEqual(players, ["Bram", "Cas", "Dirk"])


class PlayerTests(GameApiTestCase):
    def test_players_cannot_be_deleted_or_renamed(self):
        player = Player.objects.get(name="Anna")
        url = f"{PLAYERS_URL}{player.uuid}/"

        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.patch(url, {"name": "X"}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(Player.objects.filter(name="Anna").exists())

    def test_dot_only_names_are_rejected(self):
        for name in (".", ".."):
            response = self.client.post(PLAYERS_URL, {"name": name}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_player_games_are_listed(self):
        self.create_game(("Anna", 1), ("Bram", 2), ("Cas", 3))

        response = self.client.get(f"{PLAYERS_URL}Bram/games/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]["position"], 2)
        self.assertEqual(response.json()[0]["player_count"], 3)

    def test_names_with_slashes_resolve(self):
        Player.objects.create(name="a/b")
        self.create_game(("a/b", 1), ("Anna", 2))

        response = self.client.get(f"{PLAYERS_URL}a%2Fb/games/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_player_named_dates_resolves(self):
        Player.objects.create(name="dates")
        self.create_game(("dates", 1), ("Anna", 2))

        response = self.client.get(f"{PLAYERS_URL}dates/games/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_anonymous_users_cannot_probe_player_names(self):
        self.client.cookies.clear()

        existing = self.client.get(f"{PLAYERS_URL}Anna/games/")
        missing = self.client.get(f"{PLAYERS_URL}Nobody/games/")

        self.assertEqual(existing.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(missing.status_code, status.HTTP_401_UNAUTHORIZED)


class LeaderboardTests(GameApiTestCase):
    def get_leaderboard(self, start, end):
        return self.client.get(LEADERBOARD_URL, {"start": start, "end": end})

    def test_scores_and_positions(self):
        self.create_game(("Anna", 1), ("Bram", 2), ("Cas", 3))
        today = localdate().isoformat()

        response = self.get_leaderboard(today, today)

        entries = {e["player"]: e for e in response.json()}
        self.assertEqual(entries["Anna"]["position"], 1)
        self.assertEqual(entries["Anna"]["games_won"], 1)
        self.assertEqual(entries["Bram"]["average_score"], 0.5)
        self.assertEqual(entries["Cas"]["final_score"], 0.0)

    def test_query_count_does_not_grow_with_games(self):
        for _ in range(10):
            self.create_game(("Anna", 1), ("Bram", 2), ("Cas", 3))
        today = localdate().isoformat()

        with self.assertNumQueries(2):  # user lookup + results
            self.get_leaderboard(today, today)

    def test_months_follow_local_time(self):
        self.create_game(("Anna", 1), ("Bram", 2))
        # 00:30 on 1 November in Amsterdam is still 31 October in UTC
        played_at = datetime(2026, 11, 1, 0, 30, tzinfo=ZoneInfo("Europe/Amsterdam"))
        Game.objects.update(played_at=played_at)

        november = self.get_leaderboard("2026-11-01", "2026-11-30").json()
        october = self.get_leaderboard("2026-10-01", "2026-10-31").json()

        self.assertEqual(len(november), 2)
        self.assertEqual(october, [])
