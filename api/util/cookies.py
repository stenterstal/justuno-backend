from django.conf import settings

ACCESS_COOKIE_PATH = "/"
REFRESH_COOKIE_PATH = "/api/auth/"


def set_auth_cookies(response, access_token, refresh_token):
    response.set_cookie(
        key="access",
        value=str(access_token),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        path=ACCESS_COOKIE_PATH,
    )

    response.set_cookie(
        key="refresh",
        value=str(refresh_token),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=REFRESH_COOKIE_PATH,
    )

    return response


def delete_auth_cookies(response):
    response.delete_cookie("access", path=ACCESS_COOKIE_PATH, samesite=settings.COOKIE_SAMESITE)
    response.delete_cookie("refresh", path=REFRESH_COOKIE_PATH, samesite=settings.COOKIE_SAMESITE)
    # Clear the refresh cookie from its previous, narrower path
    response.delete_cookie("refresh", path="/api/auth/refresh/", samesite=settings.COOKIE_SAMESITE)
    return response
