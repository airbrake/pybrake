import os
import sys
import platform
import traceback as tb
import socket
import urllib.request, urllib.error
import queue
from concurrent import futures
import json
import time
import logging

from .notice import jsonify_notice
from .code_hunks import get_code_hunk
from .utils import logger


_ERR_IP_RATE_LIMITED = 'IP is rate limited'

_AIRBRAKE_URL_FORMAT = '{}/api/v3/projects/{}/notices'

_CONTEXT = dict(
  notifier=dict(
    name='pybrake',
    version='0.2.0',
    url='https://github.com/airbrake/pybrake',
  ),
  os=platform.platform(),
  language='Python/%s' % platform.python_version(),
  hostname=socket.gethostname(),
  versions=dict(
    python=platform.python_version(),
  ),
)


class Notifier:
  def __init__(self,
               project_id=0,
               project_key='',
               host='https://api.airbrake.io',
               **kwargs):
    self._filters = []
    self._rate_limit_reset = 0
    self._max_queue_size = kwargs.get('max_queue_size', 1000)
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

  def notify_sync(self, err):
    """Notifies Airbrake about exception.

    Under the hood notify is a shortcut for build_notice and send_notice.
    """
    notice = self.build_notice(err)
    return self.send_notice_sync(notice)

  def build_notice(self, err):
    """Builds Airbrake notice from the exception."""
    notice = dict(
      errors=self._build_errors(err),
      context=self._build_context(),
      params=dict(
        sys_executable=sys.executable,
        sys_path=sys.path,
      ),
    )
    return notice

  def send_notice_sync(self, notice):
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

    if time.time() < self._rate_limit_reset:
      notice['error'] = _ERR_IP_RATE_LIMITED
      return notice

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
      logger.error(notice['error'])
      return notice

    try:
      body = resp.read()
    except Exception as err:
      notice['error'] = err
      logger.error(notice['error'])
      return notice

    if not (200 <= resp.code < 300 or 400 <= resp.code < 500):
      notice['error'] = 'unexpected Airbrake response status code'
      notice['error_info'] = dict(code=resp.code, body=body)
      logger.error(notice['error'])
      return notice

    if resp.code == 429:
      return self._rate_limited(notice, resp)

    try:
      data = json.loads(body.decode('utf-8'))
    except Exception as err:
      notice['error'] = err
      logger.error(notice['error'])
      return notice

    if 'id' in data:
      notice['id'] = data['id']
      return notice

    if 'message' in data:
      notice['error'] = data['message']
      logger.error(notice['error'])
      return notice

    notice['error'] = 'unexpected Airbrake response'
    notice['error_info'] = dict(data=data)
    logger.error(notice['error'])
    return notice

  def _rate_limited(self, notice, resp):
    v = resp.headers.get('X-RateLimit-Delay')
    if v is None:
      notice['error'] = 'X-RateLimit-Delay header is missing'
      return notice

    try:
      delay = int(v)
    except ValueError as err:
      notice['error'] = err
      return notice

    self._rate_limit_reset = time.time() + delay

    notice['error'] = _ERR_IP_RATE_LIMITED
    return notice;

  def notify(self, err):
    """Asynchronously notifies Airbrake about exception from separate thread.

    Returns concurrent.futures.Future.
    """
    notice = self.build_notice(err)
    return self.send_notice(notice)

  def send_notice(self, notice):
    """Asynchronously sends notice to Airbrake from separate thread.

    Returns concurrent.futures.Future.
    """
    pool = self._get_thread_pool()
    if pool._work_queue.qsize() >= self._max_queue_size:
      notice['error'] = 'queue is full'
      f = futures.Future()
      f.set_result(notice)
      return f
    return pool.submit(self.send_notice_sync, notice)

  def _build_errors(self, err):
    if isinstance(err, str):
      backtrace = self._build_backtrace_frame(sys._getframe())
      return [{
        'message': err,
        'backtrace': backtrace,
      }]

    errors = []
    while err != None:
      errors.append(self._build_error(err))
      err = err.__cause__ or err.__context__
    return errors

  def _build_error(self, err):
    backtrace = self._build_backtrace_tb(err.__traceback__)
    error = dict(
      type=err.__class__.__name__,
      message=str(err),
      backtrace=backtrace,
    )
    return error

  def _build_backtrace_tb(self, tb):
    backtrace = []
    for frame, lineno in self._walk_tb(tb):
      f = self._build_frame(frame, lineno)
      if f:
        backtrace.append(f)
    return backtrace

  def _walk_tb(self, tb):
    while tb is not None:
      yield tb.tb_frame, tb.tb_lineno
      tb = tb.tb_next

  def _build_backtrace_frame(self, f):
    backtrace = []
    for frame, lineno in self._walk_stack(f):
      f = self._build_frame(frame, lineno)
      if f:
        backtrace.append(f)
    return backtrace

  def _walk_stack(self, f):
    while f is not None:
      yield f, f.f_lineno
      f = f.f_back

  def _build_frame(self, f, line):
    if f.f_locals.get('__traceback_hide__'):
      return None

    filename = f.f_code.co_filename
    func = f.f_code.co_name

    if filename.endswith('pybrake/notifier.py'):
      return None

    loader = f.f_globals.get('__loader__')
    module_name = f.f_globals.get('__name__')
    return self._frame_with_code(filename, func, line,
                                 loader=loader,
                                 module_name=module_name)

  def _frame_with_code(self, filename, func, line, loader=None, module_name=None):
    frame = dict(
      file=self._clean_filename(filename),
      function=func,
      line=line,
    )

    lines = get_code_hunk(filename, line, loader=loader, module_name=module_name)
    if lines is not None:
      frame['code'] = lines

    return frame

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

  def _get_thread_pool(self):
    if self._thread_pool is None:
      max_workers = (os.cpu_count() or 1) * 5
      self._thread_pool = futures.ThreadPoolExecutor(max_workers=max_workers)
    return self._thread_pool
