#!/usr/bin/env bash
# Render build script (runs from backend/ via rootDir).
set -o errexit

pip install -r requirements/prod.txt
python manage.py collectstatic --noinput
python manage.py migrate
