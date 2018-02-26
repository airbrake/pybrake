def get_exception():
  try:
    raise ValueError('hello')
  except Exception as err:
    return err


def build_notice_from_str(notifier, s):
    return notifier.build_notice(s)
