<div align="center">
  <h1 align="center">Justuno backend</h1>
  <p align="center">Backend for <a href="https://github.com/stenterstal/justuno-frontend">justuno-frontend</a>. </br>
    Build with <a href="https://www.django-rest-framework.org/" target="_blank">Django Rest Framework</a>. Authentication using JWT authentication with HTTP-only cookies and refresh tokens.
  </p>
  <p>
    <img src="https://github.com/stenterstal/justuno-backend/actions/workflows/docker.yaml/badge.svg">
    <a href="https://github.com/stenterstal/justuno-backend/pkgs/container/justuno-backend">
      <img src="https://img.shields.io/badge/ghcr-justuno--backend-blue?logo=github" />
    </a>
    <a href="https://github.com/stenterstal/justuno-backend/releases">
      <img src="https://img.shields.io/github/v/release/stenterstal/justuno-backend?logo=github" />
    </a>
    <a href="https://github.com/stenterstal/justuno-backend/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/stenterstal/justuno-backend?logo=github" />
    </a>
  </p>
</div>

# 🐳 Docker Compose
See <a href="https://github.com/stenterstal/justuno-frontend/blob/main/docker-compose-traefik.yaml">justuno-frontend docker-compose-traefik.yaml</a>.

The image runs in production mode and requires `DJANGO_SECRET_KEY` to be set. Generate one with:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

# 🛠️ Developing
```bash
# 1. Clone this repo
git clone https://github.com/stenterstal/justuno-backend.git

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate environment
source venv/bin/activate # Linux
.\venv\Scripts\Activate  # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run db migrations
python manage.py migrate

# 6. Run server (debug is on by default outside Docker)
python manage.py runserver 0.0.0.0:8000

# 7. Optional: create superuser for admin portal
python manage.py createsuperuser
```

# 🚀 Releasing
Docker images are built by the <a href="https://github.com/stenterstal/justuno-backend/blob/main/.github/workflows/docker.yaml">Build workflow</a>, which runs when a GitHub release is **published**.

1. Push the changes you want to release to `main`.
2. Create a release with a new tag in `MAJOR.MINOR.PATCH` format, without a `v` prefix (e.g. `1.0.1`):
   - **GitHub:** *Releases* → *Draft a new release* → *Choose a tag*, type the new version and pick *Create new tag on publish* (target `main`) → *Generate release notes* → *Publish release*
   - **CLI:** `gh release create 1.0.1 --target main --generate-notes`
3. Follow the build in the *Actions* tab. When it finishes, `ghcr.io/stenterstal/justuno-backend` has two new tags: `1.0.1` and `latest`.
4. Update the server:
   ```bash
   docker compose pull && docker compose up -d
   ```

Notes:
- Saving a release as a draft does not start a build, only publishing does.
- *Run workflow* in the Actions tab (manual trigger) rebuilds from a branch and only updates `latest`, without a version tag.
- The compose file uses `latest` for both images. When a change touches the API, release the <a href="https://github.com/stenterstal/justuno-frontend">frontend</a> too so both images match.
