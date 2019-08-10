from celery import Celery

from .celery import patch_celery
from .notifier import Notifier

app = Celery("test_celery", broker="redis://localhost", backend='redis://localhost')

notifier = Notifier(host="http://localhost:8080", environment="celery")
patch_celery(notifier)

@app.task
def getException():
    raise ValueError("Test")
