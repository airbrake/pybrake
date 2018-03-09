from flask import request
from flask.signals import got_request_exception
try:
  from flask_login import current_user
except ImportError:
  flask_login_imported = False
else:
  flask_login_imported = True

from .notifier import Notifier


def init_app(app):
  if 'pybrake' in app.extensions:
    raise ValueError('pybrake is already injected')
  if 'PYBRAKE' not in app.config:
    raise ValueError("app.config['PYBRAKE'] is not defined")

  app.extensions['pybrake'] = Notifier(**app.config['PYBRAKE'])
  got_request_exception.connect(_handle_exception, sender=app)

  return app


def _handle_exception(sender, exception, **_):
  notifier = sender.extensions['pybrake']

  notice = notifier.build_notice(exception)
  ctx = notice['context']
  ctx['method'] = request.method
  ctx['url'] = request.url

  try:
    user_addr = request.access_route[0]
  except IndexError:
    user_addr = request.remote_addr
  if user_addr:
    ctx['userAddr'] = user_addr

  if flask_login_imported and current_user.is_authenticated:
    user = dict(
      id=current_user.get_id(),
    )
    for s in ['username', 'name']:
      if hasattr(current_user, s):
        user[s] = getattr(current_user, s)
    ctx['user'] = user

  notice['params']['request'] = dict(
    form=request.form,
    json=request.json,
    files=request.files,
    cookies=request.cookies,
    headers=dict(request.headers),
    environ=request.environ,
    blueprint=request.blueprint,
    url_rule=request.url_rule,
    view_args=request.view_args,
  )

  notifier.send_notice(notice)
