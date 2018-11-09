import datetime
from flask import g, request
from pybrake.utils import logger

def setup_airbrake_middleware(app, notifier):
  app.before_request(before_request())
  app.after_request(after_request(notifier))

def before_request():
  def before_request_middleware():
    g.flask_request_start_time = datetime.datetime.now()

  return before_request_middleware

def after_request(notifier):
  def after_request_middleware(response):
    if not hasattr(g, 'flask_request_start_time'):
      logger.error("flask_request_start_time is empty")
      return response

    now = datetime.datetime.utcnow()
    dur = now - g.flask_request_start_time
    if dur == 0:
      logger.error("processing time is not valid")
      return response

    notifier.notify_request(
      method=request.method, route=str(request.endpoint),
      status_code=response.status_code, time=now, ms=dur.millisecond,
    )

    return response

  return after_request_middleware
