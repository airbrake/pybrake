import random

from celery import Celery
from pybrake.middleware.celery import patch_celery

import pybrake

app = Celery("tasks", broker="redis://localhost")

notifier = pybrake.Notifier(
    project_id=1,
    project_key="FIXME",
    environment="celery"
)
patch_celery(notifier)


@app.task
def add(x, y):
    if random.random() < 0.5:
        raise ValueError("bad luck")
    return x + y
