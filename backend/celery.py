from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from django.conf import settings

# setting the Django settings module.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings.DJANGO_SETTINGS_MODULE)
app = Celery("backend")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Looks up for task modules in Django applications and loads them
app.autodiscover_tasks()

app.conf.update(
    BROKER_URL=settings.BROKER_URL, CELERY_RESULT_BACKEND=settings.CELERY_RESULT_BACKEND
)
app.conf.broker_transport_options = {"visibility_timeout": 1209600}  # 14 days
