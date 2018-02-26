from pybrake import Notifier

from .test_helper import get_exception, build_notice_from_str


def test_build_notice_from_exception():
  notifier = Notifier()

  err = get_exception()
  notice = notifier.build_notice(err)

  errors = notice['errors']
  assert len(errors) == 1

  error = errors[0]
  assert error['type'] == 'ValueError'
  assert error['message'] == 'hello'

  backtrace = error['backtrace']
  assert len(backtrace) == 37

  frame = backtrace[0]
  assert frame['file'] == '[PROJECT_ROOT]/pybrake/test_helper.py'
  assert frame['function'] == 'get_exception'
  assert frame['line'] == 5
  assert frame['code'] == {
    3: "    raise ValueError('hello')",
    4: '  except Exception as err:',
    5: '    return err',
    6: '',
    7: ''
  }

  context = notice['context']
  assert context['notifier'] == {
    'name': 'pybrake',
    'url': 'https://github.com/airbrake/pybrake',
    'version': '0.0.1',
  }
  for k in ['os', 'language', 'hostname']:
    assert context[k]


def test_build_notice_from_str():
  notifier = Notifier()

  notice = build_notice_from_str(notifier, 'hello')

  errors = notice['errors']
  assert len(errors) == 1

  error = errors[0]
  assert error['message'] == 'hello'

  backtrace = error['backtrace']
  assert len(backtrace) == 37

  frame = backtrace[0]
  assert frame['file'] == '[PROJECT_ROOT]/pybrake/test_helper.py'
  assert frame['function'] == 'build_notice_from_str'
  assert frame['line'] == 9
  assert frame['code'] == {
    7: '',
    8: 'def build_notice_from_str(notifier, s):',
    9: '    return notifier.build_notice(s)',
  }


def test_environment():
  notifier = Notifier(environment='production')

  notice = notifier.build_notice('hello')

  assert notice['context']['environment'] == 'production'


def test_root_directory():
  notifier = Notifier(root_directory='/root/dir')

  notice = notifier.build_notice('hello')

  assert notice['context']['rootDirectory'] == '/root/dir'


def test_filter_data():
  def filter(notice):
    notice['params']['param'] = 'value'
    return notice

  notifier = Notifier()
  notifier.add_filter(filter)

  notice = notifier.notify('hello')

  assert notice['params']['param'] == 'value'


def test_filter_ignore():
  notifier = Notifier()
  notifier.add_filter(lambda notice: None)

  notice = notifier.notify('hello')

  assert notice['error'] == 'notice is filtered out'


def test_filter_ignore_lazy():
  notifier = Notifier()
  notifier.add_filter(lambda notice: None)

  future = notifier.notify_lazy('hello')
  notice = future.result()

  assert notice['error'] == 'notice is filtered out'


def test_unauthorized():
  notifier = Notifier()

  notice = notifier.notify('hello')

  assert notice['error'] == 'API key is required'


def test_unknown_host():
  notifier = Notifier(host='http://airbrake123.com')

  notice = notifier.notify('hello')

  assert str(notice['error']) == '<urlopen error [Errno -2] Name or service not known>'


def test_truncation():
  notifier = Notifier()

  notice = notifier.build_notice('hello')
  notice['params']['param'] = 'x' * 64000
  notice = notifier.send_notice(notice)

  assert len(notice['params']['param']) == 1024
