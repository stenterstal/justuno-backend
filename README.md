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

# 6. Run server with debug
DJANGO_DEBUG=True python manage.py runserver 0.0.0.0:8000

# 7. Optional: create superuser for admin portal
python manage.py createsuperuser
```