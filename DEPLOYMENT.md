# Render Deployment Notes

This project is configured for deployment with Render.

## Project root

The Django application lives in `backend/`, where `manage.py` is located.

## Render settings

Root Directory:
`backend`

Build Command:
`bash build.sh`

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

## File uploads

Assignment and lab attachments are currently stored through Django's filesystem storage.
For local development this works with `MEDIA_ROOT`.

For production, use durable object storage (such as an S3-compatible service) before
relying on uploaded attachments as permanent records. A normal Render web-service
filesystem should not be treated as permanent application storage.

The application serves submission attachments through an authenticated route so
only the submitting student or an instructor/admin can access them.
