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


_AIRBRAKE_URL_FORMAT = '{}/api/v3/projects/{}/notices'

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
  def __init__(self,
               project_id=0,
               project_key='',
               host='https://api.airbrake.io',
               **kwargs):
    self._filters = []
    self._thread_pool = None

    self._airbrake_url = _AIRBRAKE_URL_FORMAT.format(host, project_id)
    self._airbrake_headers = {'authorization': 'Bearer ' + project_key,
                              'content-type': 'application/json'}

    self._context = _CONTEXT.copy()
    self._context['rootDirectory'] = kwargs.get('root_directory', os.getcwd())
    if 'environment' in kwargs:
      self._context['environment'] = kwargs['environment']

  def close(self):
    if self._thread_pool is not None:
      self._thread_pool.shutdown()

  def add_filter(self, filter_fn):
    """Appends filter to the list.

    Filter is a function that accepts notice. Filter can modify passed
    notice or return None if notice must be ignored.
    """
    self._filters.append(filter_fn)

  def notify(self, err):
    """Notifies Airbrake about exception.

    Under the hood notify is a shortcut for build_notice and send_notice.
    """
    notice = self.build_notice(err)
    return self.send_notice(notice)

  def build_notice(self, err, depth=0):
    """Builds Airbrake notice from the exception."""
    notice = dict(
      errors=self._build_errors(err, depth=depth),
      context=self._build_context(),
      params=dict(),
    )
    return notice

  def send_notice(self, notice):
    """Sends notice to Airbrake.

    It returns notice with 2 possible new keys:
    - {'id' => str} - notice id on success.
    - {'error' => str|Exception} - error on failure.
    """
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
    except urllib.error.HTTPError as err:
      resp = err
    except Exception as err:
      notice['error'] = err
      return notice

    try:
      body = resp.read()
    except Exception as err:
      notice['error'] = err
      return notice

    if not (200 <= resp.code < 300 or 400 <= resp.code < 500):
      notice['error'] = 'unexpected Airbrake response status code'
      notice['code'] = resp.code
      notice['body'] = body
      return notice

    try:
      data = json.loads(body.decode('utf-8'))
    except Exception as err:
      notice['error'] = err
      return notice

    if 'id' in data:
      notice['id'] = data['id']
      return notice

    if 'message' in data:
      notice['error'] = data['message']
      return notice

    notice['error'] = 'unexpected Airbrake data'
    notice['data'] = data
    return notice

  def _get_thread_pool(self):
    if self._thread_pool is None:
      self._thread_pool = self._thread_pool_executor()
    return self._thread_pool

  def notify_lazy(self, err):
    """Asynchronously notifies Airbrake about exception from separate thread.

    Returns concurrent.futures.Future.
    """
    return self._get_thread_pool().submit(self.notify, err)

  def send_notice__lazy(self, notice):
    """Asynchronously sends notice to Airbrake from separate thread.

    Returns concurrent.futures.Future.
    """
    return self._get_thread_pool().submit(self.send_notice, notice)

  def _build_errors(self, err, depth=0):
    if isinstance(err, str):
      backtrace = self._build_backtrace(None, depth=depth)
      return [{
        'message': err,
        'backtrace': backtrace,
      }]

    errors = []
    while err != None:
      errors.append(self._build_error(err))
      err = err.__cause__
    return errors

  def _build_error(self, err):
    frame = err.__traceback__.tb_frame
    backtrace = self._build_backtrace(frame)
    error = dict(
      type=err.__class__.__name__,
      message=str(err),
      backtrace=backtrace,
    )
    return error

  def _build_backtrace(self, frame, depth=0):
    stack = tb.StackSummary.extract(tb.walk_stack(frame))

    backtrace = []
    i = 0
    for f in stack:
      if f.filename.endswith('pybrake/notifier.py'):
        continue

      i += 1
      if i <= depth:
        continue

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
