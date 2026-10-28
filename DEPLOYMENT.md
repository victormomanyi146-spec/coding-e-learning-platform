# Render Deployment Notes

This repository supports a unified Docker deployment that builds the React
frontend with Vite and serves the generated assets through Django. The root
`Dockerfile` builds the frontend, prepares the React entry template, and starts
Django with `UNIFIED_REACT_FRONTEND=True`.

## Production deployment architecture

The existing production service should use the repository root as its Docker
build context:

- Repository: `victormomanyi146-spec/coding-e-learning-platform`
- Branch: `main`
- Runtime: Docker
- Dockerfile path: `./Dockerfile`
- Docker build context: `.`
- Region: Oregon
- Compute plan: preserve the existing service plan
- Health check path: `/healthz/`
- Auto-deploy behavior: deploy on commits to the linked branch

Do not set `UNIFIED_REACT_FRONTEND=True` on the existing native Python service
while it remains rooted at `backend/`. That configuration does not build or copy
the React template and Vite assets, and enabling the flag alone can break page
rendering.

## Production migration preflight

Before changing the current production service from Python to Docker:

1. Confirm that `DATABASE_URL` points to the existing production PostgreSQL
   database. Never paste the connection string into chat or commit it to Git.
   If the database target is uncertain, stop and investigate first.
2. Preserve the existing production `DJANGO_SECRET_KEY` exactly.
3. Preserve all existing environment variables, including database, mail-provider,
   file-storage and application-specific settings. Do not copy staging values
   into production.
4. Keep `DJANGO_DEBUG=False` and verify that `DJANGO_CSRF_TRUSTED_ORIGINS`
   includes the production HTTPS origin.
5. Confirm that the runtime change targets the existing production service and
   keeps the existing service URL.

## Blueprint management

A local edit to `render.yaml` does not by itself change the live service.

Before applying a Blueprint, confirm whether the existing production service is
already managed by a Blueprint. Do not create a second production service by
accident. If no existing Blueprint manages it, review the existing-service
runtime-change procedure in the Render Dashboard before choosing an approach.

## Post-deploy verification

Verify the following after an approved deployment:

- `/healthz/` returns a successful HTTP response.
- `/` serves the React application shell.
- JavaScript and CSS assets return HTTP 200.
- `/login`, `/courses`, `/assessments`, `/projects`, `/certificates`, and
  `/notifications` serve the React application shell.
- Student, instructor and admin authentication and permissions work against the
  existing production database.
- Course progress, submission grading, certificates and notifications work.
- Existing email delivery and uploaded-file access remain configured.

Route-shell responses alone do not establish interactive end-to-end correctness.
Test the workflows in staging before changing production.

## Important security note

The application contains a Python code runner that executes submitted code using
the server's Python interpreter. Do not expose that runner publicly until it is
moved into an isolated sandbox with strict CPU, memory, filesystem, process and
network restrictions.

Production should use PostgreSQL. SQLite is available for local development.

## File uploads

Assignment and lab attachments currently use Django's filesystem storage through
`MEDIA_ROOT`. A normal Render web-service filesystem should not be treated as
permanent storage. Configure durable object storage, such as an S3-compatible
service, before relying on uploaded attachments as permanent records.

Submission attachments are served through an authenticated route that limits
access to the submitting student and authorized instructors or administrators.
