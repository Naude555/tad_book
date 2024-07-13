#!/bin/sh

python3 manage.py collectstatic
# celery --app=config worker -l INFO -Q celery,celery:1,celery:2,celery:3
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 8 --log-level info


exec "$@"
