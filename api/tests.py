from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()

LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"
LOGOUT_URL = "/api/auth/logout/"
PROTECTED_URL = "/api/players/"


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
