from celery import Celery

from .celery import patch_celery
from .notifier import Notifier

app = Celery("test_celery", broker="redis://localhost", backend="redis://localhost")

notifier = Notifier(
    host="http://localhost:8080", environment="celery", apm_disabled=True
)
patch_celery(notifier)


@app.task
def raise_error():
    raise ValueError("Test")
