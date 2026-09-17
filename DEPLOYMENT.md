# Render Deployment Notes

This project is configured for deployment with Render.

## Project root

The Django application lives in `backend/`, where `manage.py` is located.

## Render settings

Root Directory:
`backend`

Build Command:
`./build.sh`

Start Command:
`gunicorn config.wsgi:application`

## Required environment variables

- DJANGO_SECRET_KEY: generate a secure value in Render
- DJANGO_DEBUG: False
- DJANGO_TIME_ZONE: Africa/Nairobi
- DJANGO_CSRF_TRUSTED_ORIGINS: your Render URL, for example https://your-service.onrender.com
- DATABASE_URL: PostgreSQL connection string

## Important

The application currently contains a Python code runner. The runner executes submitted Python code with the server's Python interpreter. Do not expose that runner publicly until it is moved into an isolated sandbox/container with strict CPU, memory, filesystem, process, and network restrictions.

SQLite remains available for local development. Production should use PostgreSQL.
