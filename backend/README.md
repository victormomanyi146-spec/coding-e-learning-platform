# Coding E-Learning Platform — Backend

This directory contains the Django application.

## Applications

- `academy`: courses, modules, lessons, activities, submissions, progress, and enrollment
- `accounts`: custom user model, registration, authentication, and student token login API
- `config`: Django project configuration

## Local setup

```powershell
cd "D:\Resume Projects\Coding E-Learning Platform\backend"

python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata academy_content.json
python manage.py check
python manage.py test
python manage.py runserver
```

## URLs

- `/` — Coding Academy home
- `/courses/` — course catalogue
- `/courses/my-courses/` — enrolled courses
- `/accounts/login/` — student login
- `/accounts/register/` — student registration
- `/admin/` — Django administration
- `/api/accounts/login/` — student token login API

## Deployment

Render uses:

```text
Root Directory: backend
Build Command: ./build.sh
Start Command: gunicorn config.wsgi:application
```

Production should use PostgreSQL through `DATABASE_URL`.

## Code execution warning

The Python code runner is intentionally disabled when `DJANGO_DEBUG=False`. Do not enable public code execution until submitted code is isolated in a hardened sandbox.
