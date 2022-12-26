release: python manage.py migrate
web: gunicorn backend.wsgi:application --log-file -
celery_worker: celery -A backend worker -l INFO -n default@%n