#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn voting_system.config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${GUNICORN_WORKERS:-3}"
