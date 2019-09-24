import functools

import celery.exceptions as excs
import celery.app.trace as trace

from . import metrics
from .queues import QueueMetric


_CELERY_EXCEPTIONS = (excs.Retry, excs.Ignore, excs.Reject)


def patch_celery(notifier):
    old_build_tracer = trace.build_tracer

    def build_tracer(name, task, *args, **kwargs):
        if getattr(task, "_ab_patched", False):
            return old_build_tracer(name, task, *args, **kwargs)

        task._ab_patched = True
        task.__call__ = _wrap_task_call(task, task.__call__, notifier=notifier)
        task.run = _wrap_task_call(task, task.run, notifier=notifier)

        return old_build_tracer(name, task, *args, **kwargs)

    trace.build_tracer = build_tracer


def _wrap_task_call(task, fn, *, notifier=None):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        metric = QueueMetric(queue=task.name)
        metrics.set_active(metric)

        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if not isinstance(exc, _CELERY_EXCEPTIONS):
                notifier.notify(exc)
            raise exc
        finally:
            notifier.queues.notify(metric)
            metrics.set_active(None)

    return wrapper
