# Patch notes 0.1

## Breaking changes

### `DJANGO_SECRET_KEY` is now required in production
The Docker image now runs in production mode (`DJANGO_ENV=production`) and won't start without `DJANGO_SECRET_KEY`. It fails with:

```
django.core.exceptions.ImproperlyConfigured: DJANGO_SECRET_KEY must be set in production.
```

Generate a key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Add it to the backend service in your `docker-compose`:

```yaml
services:
  backend:
    environment:
      DJANGO_SECRET_KEY: "<your generated key>"
```

Keep the key out of version control. For example, use an `.env` file next to your compose file and write `DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY}`.

### Everyone is logged out once after upgrading
Login tokens are signed with the secret key, so every existing session stops working once the new key is in place. Everyone needs to log in again once.

### Running outside Docker defaults to development mode
Outside the Docker image, the backend now defaults to development mode: `DEBUG` is on and a built-in, insecure dev key is used. If you run it in production without Docker, you must set both of these yourself:

```bash
DJANGO_ENV=production
DJANGO_SECRET_KEY=<your generated key>
```

`DJANGO_DEBUG` can still override the debug setting either way. Local development no longer needs `DJANGO_DEBUG=True`.

## Other changes worth knowing

- **Login is limited to 5 attempts per minute per client IP**, and returns `429 Too Many Requests` after that. The client IP comes from `X-Forwarded-For`. Traefik sets that header by default. If your proxy doesn't set it, all users share one limit.
- **Logout now revokes the refresh token**, so a copied refresh cookie can't be used after logout.
- **Refreshing as a deactivated or deleted user now returns `401`** and clears the auth cookies. Previously, deactivated users could keep refreshing.
- **Refresh cookie:**
  - Its path changed from `/api/auth/refresh/` to `/api/auth/`. The frontend doesn't need any changes.
  - Its lifetime now matches the token lifetime: 7 days instead of 1.
