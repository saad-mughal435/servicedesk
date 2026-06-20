#!/usr/bin/env bash
# Render build step: install deps, collect static, run migrations, and
# populate demo data on first deploy (seed is idempotent — it only creates
# tickets when the database is empty).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

if [ "$DEMO_MODE" = "true" ]; then
  python manage.py seed
fi
