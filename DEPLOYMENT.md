# Tech Haven — Render Deployment Notes

## Target production architecture

The planned migration changes the existing `coding-e-learning-platform` web service from the native Python runtime to the repository-root Docker build.

- Repository: `victormomanyi146-spec/coding-e-learning-platform`
- Linked production branch: `main`
- Dockerfile: `./Dockerfile`
- Docker build context: repository root (`.`)
- Region: Oregon
- Health check: `/healthz/`
- Frontend: React built with Vite and served through Django

This document describes the target configuration. It does not mean the live production service has already been migrated.

## Production safety requirements

Before changing or syncing the production service:

1. Confirm the target is the existing production service and that its URL and PostgreSQL database will be retained.
2. Preserve the existing `DJANGO_SECRET_KEY`, `DATABASE_URL`, and all mail, file-storage, authentication, and application-specific environment variables.
3. Keep production debug mode disabled and verify the production HTTPS origin remains in the CSRF trusted origins.
4. Preserve the existing compute plan and other service settings.
5. Confirm whether the existing service is already managed by a Render Blueprint. Do not manage the same service through a second Blueprint.
6. Review the actual configuration changes Render proposes before applying or syncing them.

The root `render.yaml` intentionally omits existing production secrets and service-specific environment variables. It is intended to configure the existing service, not to create a separately configured production service.

## Post-migration verification

After an explicitly approved deployment, verify:

- `/healthz/` returns a successful response.
- `/` serves the React application shell.
- JavaScript and CSS assets load successfully.
- `/login`, `/courses`, `/assessments`, `/projects`, `/certificates`, and `/notifications` load correctly.
- Student, instructor, and administrator authentication and permissions work.
- Course progress, assessment submissions, grading, certificates, and notifications work against the existing production database.
- Email delivery and existing uploaded-file access remain configured.

Successful route responses alone do not prove interactive end-to-end functionality. Test critical workflows in staging before production migration.

## Code runner security

The application contains a Python code runner. Do not expose arbitrary submitted code to the production server interpreter without an isolated execution environment with strict CPU, memory, filesystem, process, and network restrictions.

## Uploaded files

Assignment and lab attachments use Django filesystem storage through `MEDIA_ROOT`. A normal Render web-service filesystem should not be treated as durable storage. Configure and verify durable object storage before relying on uploaded attachments as permanent records.

Attachment downloads must remain protected by authorization checks so only the submitting student and authorized instructors or administrators can access them.
