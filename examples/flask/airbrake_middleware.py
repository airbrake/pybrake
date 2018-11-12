import time
from flask import g, request
from pybrake.utils import logger

def setup_airbrake_middleware(app, notifier):
  app.before_request(before_request())
  app.after_request(after_request(notifier))

def before_request():
  def before_request_middleware():
    g.request_start_time = time.time()

  return before_request_middleware

def after_request(notifier):
  def after_request_middleware(response):
    if not hasattr(g, 'request_start_time'):
      logger.error("request_start_time is empty")
      return response

    notifier.notify_request(
      method=request.method, route=str(request.endpoint), status_code=response.status_code,
      start_time=g.request_start_time, end_time=time.time())

    return response

  return after_request_middleware
