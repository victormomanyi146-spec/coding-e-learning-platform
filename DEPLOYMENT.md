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

## Instructor application documents

Instructor CVs and qualification records use a separate private storage backend.
Local development defaults to filesystem storage outside `MEDIA_ROOT`. Deployments
with `DJANGO_DEBUG=False` default to S3-compatible storage and fail closed if required
bucket or region settings are missing.

Configure these variables on the deployment service:

- `INSTRUCTOR_DOCUMENT_STORAGE=s3`
- `INSTRUCTOR_DOCUMENTS_S3_BUCKET`: private bucket name
- `INSTRUCTOR_DOCUMENTS_S3_REGION`: provider-supported bucket region

Optional variables:

- `INSTRUCTOR_DOCUMENTS_S3_ENDPOINT_URL`: endpoint for an S3-compatible provider
- `INSTRUCTOR_DOCUMENTS_S3_PREFIX`: optional object-key prefix
- `INSTRUCTOR_DOCUMENTS_S3_ACCESS_KEY` and `INSTRUCTOR_DOCUMENTS_S3_SECRET_KEY`:
  access credentials when required
- `INSTRUCTOR_DOCUMENTS_S3_SESSION_TOKEN`: optional temporary-credential token
- `INSTRUCTOR_DOCUMENTS_S3_QUERYSTRING_EXPIRE`: signed URL lifetime in seconds (default 300)

Keep the bucket private and enable the provider's public-access blocking controls.
Never commit credentials or share their values. Documents should be retrieved only
through the administrator-authorized download endpoint, not public media URLs.

## Other file uploads

Assignment and lab attachments still use the general filesystem storage. Configure
and verify durable storage for those uploads separately before treating them as
permanent records. The existing authenticated attachment route remains in place.
