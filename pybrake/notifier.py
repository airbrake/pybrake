import os
import platform
import traceback as tb
import socket
import urllib.request, urllib.error
import queue
from concurrent.futures import ThreadPoolExecutor
import json

from .notice import jsonify_notice
from .code_hunks import get_code_hunk


_AIRBRAKE_URL_FORMAT = 'https://{}/api/v3/projects/{}/notices'

_CONTEXT = dict(
  notifier=dict(
    name='pybrake',
    version='0.0.1',
    url='https://github.com/airbrake/pybrake',
  ),
  os=platform.platform(),
  language='Python/%s' % platform.python_version(),
  hostname=socket.gethostname(),
)


class Notifier:
  _filters = []
  _context = _CONTEXT.copy()

  _thread_pool = None

  def __init__(self, project_id=0, project_key='', host='api.airbrake.io', **kwargs):
    self._airbrake_url = _AIRBRAKE_URL_FORMAT.format(host, project_id)
    self._airbrake_headers = {'authorization': 'Bearer ' + project_key,
                              'content-type': 'application/json'}

    self._context['rootDirectory'] = kwargs.get('root_directory', os.getcwd())
    if 'environment' in kwargs:
      self._context['environment'] = kwargs['environment']

  def add_filter(self, filter_fn):
    self._filters.append(filter_fn)

  # Returns concurrent.futures.Future.
  def notify_lazy(self, err):
    if self._thread_pool is None:
      self._thread_pool = self._thread_pool_executor()

    return self._thread_pool.submit(self.notify, err)

  def notify(self, err):
    notice = self.build_notice(err)
    return self.send_notice(notice)

  def build_notice(self, err):
    errors = []
    while err != None:
      errors.append(self._build_error(err))
      err = err.__cause__

    notice = dict(
      errors=errors,
      context=self._build_context(),
      params=dict(),
      session=dict(),
      environment=dict(),
    )

    return notice

  def send_notice(self, notice):
    for fn in self._filters:
      r = fn(notice)
      if r is None:
        notice['error'] = 'notice is filtered out'
        return notice
      notice = r

    data = jsonify_notice(notice)
    req = urllib.request.Request(self._airbrake_url,
                                 data=data,
                                 headers=self._airbrake_headers)

    try:
      resp = urllib.request.urlopen(req, timeout=5)
    except urllib.error.URLError as err:
      notice['error'] = err
      return notice
    except urllib.error.HTTPError as err:
      resp = err

    body = resp.read()

    if 200 <= resp.code < 300:
      data = json.loads(body.decode('utf-8'))
      notice['id'] = data['id']
      return notice

    if 400 <= resp.code < 500:
      data = json.loads(body.decode('utf-8'))
      notice['error'] = data['message']
      return notice

    return dict(error='unexpected Airbrake response',
                code=resp.code,
                body=body)

  def _build_error(self, err):
    error = dict(
      type=err.__class__.__name__,
      message=str(err),
      backtrace=self._build_backtrace(err),
    )
    return error

  def _build_backtrace(self, err):
    frame = err.__traceback__.tb_frame
    stack = tb.StackSummary.extract(tb.walk_stack(frame))

    backtrace = []
    for f in stack:
      filename = f.filename

      frame = dict(
        file=self._clean_filename(f.filename),
        function=f.name,
        line=f.lineno,
      )

      lines = get_code_hunk(f.filename, f.lineno)
      if lines is not None:
        frame['code'] = lines

      backtrace.append(frame)

    return backtrace

  def _clean_filename(self, s):
    if '/lib/python' in s and '/site-packages/' in s:
      needed = '/site-packages/'
      ind = s.find(needed)
      if ind > -1:
        s = '[SITE_PACKAGES]/' + s[ind+len(needed):]
        return s

    s = s.replace(self._context['rootDirectory'], '[PROJECT_ROOT]')
    return s

  def _build_context(self):
    ctx = self._context.copy()
    return ctx

  def _thread_pool_executor(self):
    pool = ThreadPoolExecutor()
    if pool._work_queue is None:
      raise ValueError('can not patch ThreadPoolExecutor')
    pool._work_queue = queue.Queue(maxsize=1000)
    return pool
