#!/usr/bin/env bash
set -euo pipefail

cd /app/backend
python manage.py migrate --noinput
python manage.py shell -c 'from academy.models import Course; from django.core.management import call_command; Course.objects.exists() or call_command("loaddata", "academy_content.json")'
# Provision instructors separately; do not reset account credentials on every startup.
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}"
