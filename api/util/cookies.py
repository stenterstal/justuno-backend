from django.conf import settings


def set_auth_cookies(response, access_token, refresh_token):
    response.set_cookie(
        key="access",
        value=str(access_token),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="Lax",
        max_age=300,
        path="/",
    )

    response.set_cookie(
        key="refresh",
        value=str(refresh_token),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="Lax",
        max_age=86400,
        path="/api/auth/refresh/",
    )

    return response